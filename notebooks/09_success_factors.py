# %% [markdown]
# # NB09 — Success Factor Discovery
#
# **Goal:** Predict product success on Amazon and identify which factors drive it
# using XGBoost + SHAP. This powers Health Check mode (Q6-7): "How does my product
# compare?" and "What am I doing wrong?"
#
# **Target:** Top 25% by estimated_revenue within subcategory = 1 (success), rest = 0.
# Category-relative because our thesis says success is category-dependent.
#
# **Data leakage guard:** bought_last_month and estimated_revenue are EXCLUDED from
# features — they ARE the target. Only listing-visible attributes are used.

# %% — Imports & DB Connection
import os
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.model_selection import train_test_split
from sklearn.metrics import (classification_report, confusion_matrix,
                             roc_auc_score, roc_curve, f1_score, accuracy_score)
import xgboost as xgb
import shap
import pickle

# DB path — from notebooks/ folder
DB_PATH = os.path.join(os.path.dirname(os.getcwd()), 'data', 'amazon_intelligence.duckdb')
print(f"DB: {DB_PATH}")
print(f"Exists: {os.path.exists(DB_PATH)}")

con = duckdb.connect(DB_PATH, read_only=False)
con.execute(f"SET temp_directory='{os.path.join(os.path.dirname(os.getcwd()), 'data', 'tmp')}'")

# Chart save setup
CHART_DIR = os.path.join('charts', '09_success_factors')
os.makedirs(CHART_DIR, exist_ok=True)

def save_chart(fig, name):
    """Save as HTML always, PNG with try/except for kaleido."""
    fig.write_html(os.path.join(CHART_DIR, f"{name}.html"))
    try:
        fig.write_image(os.path.join(CHART_DIR, f"{name}.png"), width=1200, height=700, scale=2)
        print(f"Saved: {name}.html + .png")
    except Exception as e:
        print(f"Saved: {name}.html (PNG failed: {e})")

# %% — Schema Discovery
print("=== silver_products columns ===")
print(con.execute("DESCRIBE silver_products").fetchdf()[['column_name', 'column_type']].to_string())
print(f"\nTotal: {con.execute('SELECT COUNT(*) FROM silver_products').fetchone()[0]:,}")
print(f"Active (bought_last_month > 0): {con.execute('SELECT COUNT(*) FROM silver_products WHERE bought_last_month > 0').fetchone()[0]:,}")

# %% — Feature Extraction + Target Engineering
print("Extracting features with category-relative target...")

df = con.execute("""
    WITH ranked AS (
        SELECT
            asin,
            subcategory,
            -- RAW FEATURES (listing-visible)
            price,
            rating,
            review_count,
            title_length,
            CAST(is_best_seller AS INTEGER) AS is_best_seller,
            COALESCE(has_brand, 0) AS has_brand,
            COALESCE(has_features, 0) AS has_features,
            COALESCE(has_description, 0) AS has_description,
            COALESCE(has_store, 0) AS has_store,
            COALESCE(discount_pct, 0) AS discount_pct,
            COALESCE(is_mcauley_matched, 0) AS is_mcauley_matched,
            -- CATEGORY-RELATIVE FEATURES
            PERCENT_RANK() OVER (PARTITION BY subcategory ORDER BY price) AS price_rank,
            PERCENT_RANK() OVER (PARTITION BY subcategory ORDER BY review_count) AS reviews_rank,
            PERCENT_RANK() OVER (PARTITION BY subcategory ORDER BY title_length) AS title_length_rank,
            -- TARGET: revenue quartile within subcategory
            estimated_revenue,
            NTILE(4) OVER (PARTITION BY subcategory ORDER BY estimated_revenue) AS revenue_quartile
        FROM silver_products
        WHERE bought_last_month > 0
          AND price > 0
          AND rating > 0
    )
    SELECT
        asin,
        subcategory,
        price,
        rating,
        review_count,
        title_length,
        is_best_seller,
        has_brand,
        has_features,
        has_description,
        has_store,
        discount_pct,
        is_mcauley_matched,
        price_rank,
        reviews_rank,
        title_length_rank,
        estimated_revenue,
        revenue_quartile,
        CASE WHEN revenue_quartile = 4 THEN 1 ELSE 0 END AS is_success
    FROM ranked
""").fetchdf()

print(f"Products: {len(df):,}")
print(f"Subcategories: {df['subcategory'].nunique()}")
print(f"\nTarget distribution:")
print(f"  Success (top 25%): {df['is_success'].sum():,} ({df['is_success'].mean()*100:.1f}%)")
print(f"  Not success: {(1-df['is_success']).sum():,} ({(1-df['is_success']).mean()*100:.1f}%)")

# %% — Define Feature Set
# SAFE: listing-visible attributes only
# EXCLUDED: bought_last_month, estimated_revenue (= target), revenue_quartile
FEATURE_COLS = [
    'price', 'rating', 'review_count', 'title_length',
    'is_best_seller', 'has_brand', 'has_features', 'has_description',
    'has_store', 'discount_pct', 'is_mcauley_matched',
    'price_rank', 'reviews_rank', 'title_length_rank'
]

TARGET = 'is_success'

X = df[FEATURE_COLS].copy()
y = df[TARGET].copy()

print(f"Feature matrix: {X.shape}")
print(f"\nNaN counts:")
print(X.isna().sum())

# Fill any remaining NaN (shouldn't be many with COALESCE in SQL)
X = X.fillna(0)

# %% — Chart 1: Target Distribution
fig = px.bar(
    x=['Not Success (Q1-Q3)', 'Success (Top 25%)'],
    y=[len(y) - y.sum(), y.sum()],
    text=[f"{len(y) - y.sum():,}<br>({(1-y.mean())*100:.1f}%)",
          f"{y.sum():,}<br>({y.mean()*100:.1f}%)"],
    labels={'x': 'Class', 'y': 'Product Count'},
    title='Target Distribution: Success = Top 25% Revenue in Subcategory',
    color_discrete_sequence=['#EF553B', '#636EFA']
)
fig.update_traces(textposition='outside')
fig.update_layout(template='plotly_white', width=700, height=450, showlegend=False)
save_chart(fig, '01_target_distribution')
fig.show()

# %% — Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train):,} ({y_train.mean()*100:.1f}% success)")
print(f"Test:  {len(X_test):,} ({y_test.mean()*100:.1f}% success)")

# %% — XGBoost Model
print("Training XGBoost...")

model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    scale_pos_weight=(len(y_train) - y_train.sum()) / y_train.sum(),  # handle imbalance
    random_state=42,
    eval_metric='auc',
    early_stopping_rounds=20,
    n_jobs=-1
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50
)

# Predictions
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print(f"\n=== Test Set Performance ===")
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
print(f"F1 Score:  {f1_score(y_test, y_pred):.4f}")
print(f"ROC AUC:   {roc_auc_score(y_test, y_prob):.4f}")
print(f"\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Not Success', 'Success']))

# %% — Chart 2: Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
cm_pct = cm / cm.sum() * 100

fig = px.imshow(
    cm, text_auto=True,
    labels=dict(x='Predicted', y='Actual', color='Count'),
    x=['Not Success', 'Success'],
    y=['Not Success', 'Success'],
    color_continuous_scale='Blues',
    title=f'Confusion Matrix (Accuracy: {accuracy_score(y_test, y_pred):.1%})'
)
fig.update_layout(width=600, height=500, template='plotly_white')
save_chart(fig, '02_confusion_matrix')
fig.show()

# %% — Chart 3: ROC Curve
fpr, tpr, _ = roc_curve(y_test, y_prob)
auc_score = roc_auc_score(y_test, y_prob)

fig = go.Figure()
fig.add_trace(go.Scatter(x=fpr, y=tpr, mode='lines',
                         name=f'XGBoost (AUC = {auc_score:.3f})',
                         line=dict(color='#636EFA', width=2)))
fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines',
                         name='Random', line=dict(dash='dash', color='gray')))
fig.update_layout(
    title='ROC Curve — Success Prediction',
    xaxis_title='False Positive Rate',
    yaxis_title='True Positive Rate',
    template='plotly_white', width=700, height=550
)
save_chart(fig, '03_roc_curve')
fig.show()

# %% — Chart 4: XGBoost Built-in Feature Importance
importance = pd.DataFrame({
    'feature': FEATURE_COLS,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=True)

fig = px.bar(
    importance, x='importance', y='feature', orientation='h',
    title='XGBoost Feature Importance (Gain)',
    labels={'importance': 'Importance (Gain)', 'feature': 'Feature'},
    color_discrete_sequence=['#636EFA']
)
fig.update_layout(template='plotly_white', width=900, height=550)
save_chart(fig, '04_xgb_feature_importance')
fig.show()

print("\nTop 5 features:")
for _, row in importance.tail(5).iterrows():
    print(f"  {row['feature']}: {row['importance']:.4f}")

# %% — SHAP Values
print("Computing SHAP values (this may take a minute)...")

# Use a sample for SHAP if dataset is large
SHAP_SAMPLE = min(20000, len(X_test))
np.random.seed(42)
shap_idx = np.random.choice(len(X_test), SHAP_SAMPLE, replace=False)
X_shap = X_test.iloc[shap_idx]

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_shap)

print(f"SHAP values shape: {shap_values.shape}")
print(f"Sample size: {SHAP_SAMPLE:,}")

# %% — Chart 5: SHAP Summary (Beeswarm)
# Save as matplotlib figure, then convert to plotly-compatible PNG
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig_shap, ax = plt.subplots(figsize=(12, 7))
shap.summary_plot(shap_values, X_shap, feature_names=FEATURE_COLS,
                  show=False, max_display=14)
plt.title('SHAP Summary — What Drives Product Success?', fontsize=14, pad=20)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '05_shap_summary.png'), dpi=200, bbox_inches='tight')
plt.close()
print("Saved: 05_shap_summary.png")

# %% — Chart 6: SHAP Bar Plot (Mean Absolute)
mean_abs_shap = pd.DataFrame({
    'feature': FEATURE_COLS,
    'mean_abs_shap': np.abs(shap_values).mean(axis=0)
}).sort_values('mean_abs_shap', ascending=True)

fig = px.bar(
    mean_abs_shap, x='mean_abs_shap', y='feature', orientation='h',
    title='SHAP Feature Importance — Mean |SHAP Value|',
    labels={'mean_abs_shap': 'Mean |SHAP Value|', 'feature': 'Feature'},
    color_discrete_sequence=['#EF553B']
)
fig.update_layout(template='plotly_white', width=900, height=550)
save_chart(fig, '06_shap_bar')
fig.show()

# %% — Chart 7: SHAP Dependence Plot — Top 3 Features
top_features = mean_abs_shap.tail(3)['feature'].tolist()[::-1]

fig = make_subplots(rows=1, cols=3, subplot_titles=top_features,
                    horizontal_spacing=0.08)

for i, feat in enumerate(top_features):
    feat_idx = FEATURE_COLS.index(feat)
    col = i + 1
    fig.add_trace(
        go.Scatter(
            x=X_shap[feat].values,
            y=shap_values[:, feat_idx],
            mode='markers',
            marker=dict(size=3, opacity=0.3, color='#636EFA'),
            showlegend=False
        ),
        row=1, col=col
    )
    fig.update_xaxes(title_text=feat, row=1, col=col)
    fig.update_yaxes(title_text='SHAP Value' if col == 1 else '', row=1, col=col)

fig.update_layout(
    title_text='SHAP Dependence — Top 3 Features',
    template='plotly_white', width=1200, height=450
)
save_chart(fig, '07_shap_dependence')
fig.show()

# %% — Chart 8: Feature Impact Direction
# For each feature: what's the avg SHAP when feature is high vs low?
impact_data = []
for i, feat in enumerate(FEATURE_COLS):
    vals = X_shap[feat].values
    shap_col = shap_values[:, i]
    median_val = np.median(vals)
    high_mask = vals > median_val
    low_mask = vals <= median_val

    impact_data.append({
        'feature': feat,
        'avg_shap_high': shap_col[high_mask].mean() if high_mask.sum() > 0 else 0,
        'avg_shap_low': shap_col[low_mask].mean() if low_mask.sum() > 0 else 0,
    })

impact_df = pd.DataFrame(impact_data)
impact_df['direction'] = impact_df['avg_shap_high'] - impact_df['avg_shap_low']
impact_df = impact_df.sort_values('direction')

fig = px.bar(
    impact_df, x='direction', y='feature', orientation='h',
    title='Feature Impact Direction: High Value → Success (+) or Failure (−)?',
    labels={'direction': 'SHAP Shift (High − Low)', 'feature': 'Feature'},
    color='direction',
    color_continuous_scale='RdBu',
    color_continuous_midpoint=0
)
fig.update_layout(template='plotly_white', width=900, height=550)
save_chart(fig, '08_feature_direction')
fig.show()

# %% — Chart 9: Example Product Waterfall (SHAP individual explanation)
# Pick a successful product and a struggling product
success_idx = np.where((y_test.iloc[shap_idx].values == 1) & (y_prob[shap_idx] > 0.8))[0]
struggle_idx = np.where((y_test.iloc[shap_idx].values == 0) & (y_prob[shap_idx] < 0.2))[0]

if len(success_idx) > 0 and len(struggle_idx) > 0:
    # Successful product waterfall
    s_idx = success_idx[0]
    fig_s, ax = plt.subplots(figsize=(12, 6))
    shap.waterfall_plot(
        shap.Explanation(
            values=shap_values[s_idx],
            base_values=explainer.expected_value,
            data=X_shap.iloc[s_idx],
            feature_names=FEATURE_COLS
        ),
        show=False, max_display=14
    )
    plt.title('Why This Product Succeeds — SHAP Waterfall', fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_DIR, '09a_waterfall_success.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("Saved: 09a_waterfall_success.png")

    # Struggling product waterfall
    f_idx = struggle_idx[0]
    fig_f, ax = plt.subplots(figsize=(12, 6))
    shap.waterfall_plot(
        shap.Explanation(
            values=shap_values[f_idx],
            base_values=explainer.expected_value,
            data=X_shap.iloc[f_idx],
            feature_names=FEATURE_COLS
        ),
        show=False, max_display=14
    )
    plt.title('Why This Product Struggles — SHAP Waterfall', fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_DIR, '09b_waterfall_struggle.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("Saved: 09b_waterfall_struggle.png")
else:
    print(f"Could not find clear success ({len(success_idx)}) or struggle ({len(struggle_idx)}) examples")

# %% — Chart 10: Success Rate by Feature Buckets (Top 4 features)
top4 = mean_abs_shap.tail(4)['feature'].tolist()[::-1]
fig = make_subplots(rows=2, cols=2, subplot_titles=top4, vertical_spacing=0.12)

for i, feat in enumerate(top4):
    row, col = i // 2 + 1, i % 2 + 1

    # Create 5 buckets
    temp = pd.DataFrame({'feat': df[feat], 'success': df['is_success']})
    temp['bucket'] = pd.qcut(temp['feat'], q=5, duplicates='drop')
    bucket_rates = temp.groupby('bucket', observed=True)['success'].mean().reset_index()
    bucket_rates['bucket_str'] = bucket_rates['bucket'].astype(str)

    fig.add_trace(
        go.Bar(x=bucket_rates['bucket_str'], y=bucket_rates['success'],
               marker_color='#636EFA', showlegend=False),
        row=row, col=col
    )
    fig.update_yaxes(title_text='Success Rate', row=row, col=col)

fig.update_layout(
    title_text='Success Rate by Feature Quintiles — Top 4 Features',
    template='plotly_white', width=1100, height=700
)
save_chart(fig, '10_success_rate_by_feature')
fig.show()

# %% — Save Model & SHAP Artifacts
MODEL_DIR = os.path.join(os.path.dirname(os.getcwd()), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

model_artifacts = {
    'model': model,
    'feature_cols': FEATURE_COLS,
    'target': TARGET,
    'shap_values': shap_values,
    'shap_expected_value': explainer.expected_value,
    'shap_feature_names': FEATURE_COLS,
    'mean_abs_shap': mean_abs_shap,
    'accuracy': accuracy_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred),
    'auc': roc_auc_score(y_test, y_prob),
}

artifact_path = os.path.join(MODEL_DIR, 'success_factors.pkl')
with open(artifact_path, 'wb') as f:
    pickle.dump(model_artifacts, f)
print(f"Model artifacts saved: {artifact_path}")

# Also save the XGBoost model separately for Streamlit
model_path = os.path.join(MODEL_DIR, 'success_model.json')
model.save_model(model_path)
print(f"XGBoost model saved: {model_path}")

# %% — Summary & Findings
print(f"""
╔══════════════════════════════════════════════════════════════╗
║           NB09 — SUCCESS FACTOR DISCOVERY SUMMARY           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Model Performance:                                          ║
║    Accuracy: {accuracy_score(y_test, y_pred):.4f}                                       ║
║    F1 Score: {f1_score(y_test, y_pred):.4f}                                       ║
║    ROC AUC:  {roc_auc_score(y_test, y_prob):.4f}                                       ║
║                                                              ║
║  Charts: 10 (+ 2 waterfall PNGs)                             ║
║  Model artifact: models/success_factors.pkl                  ║
║  XGBoost model: models/success_model.json                    ║
║                                                              ║
║  Findings to record (fill after reviewing SHAP):             ║
║  #89:  [Top predictive feature and its SHAP impact]          ║
║  #90:  [Model accuracy — what's predictable vs not]          ║
║  #91:  [is_best_seller circularity — how much does it leak?] ║
║  #92:  [Listing quality features — do they matter?]          ║
║  #93:  [Price direction — does higher price help or hurt?]   ║
║  #94:  [Review count — threshold effect?]                    ║
║  #95:  [Category-relative vs absolute features]              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

# %% — Cleanup
con.close()
print("Done. Connection closed.")
