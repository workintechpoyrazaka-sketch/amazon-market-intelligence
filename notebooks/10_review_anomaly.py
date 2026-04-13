# %% [markdown]
# # NB10 — Review Anomaly Detection
#
# **Goal:** Flag products with suspicious review patterns using Isolation Forest.
# Powers Review Trust Score mode (Q11: "Can I trust these reviews?").
#
# **Approach:** Unsupervised — no labeled "fake" reviews exist. Isolation Forest
# finds products whose review patterns are unusual vs the population.
# Unusual ≠ proven fake, but it's the right signal for a trust score.
#
# **Data source:** gold_product_review_trust (419K rows) — already aggregated,
# no 526M row scan needed.

# %% — Imports & DB Connection
import os
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import pickle

# DB path — from notebooks/ folder
DB_PATH = os.path.join(os.path.dirname(os.getcwd()), 'data', 'amazon_intelligence.duckdb')
print(f"DB: {DB_PATH}")
print(f"Exists: {os.path.exists(DB_PATH)}")

con = duckdb.connect(DB_PATH, read_only=False)
con.execute(f"SET temp_directory='{os.path.join(os.path.dirname(os.getcwd()), 'data', 'tmp')}'")

# Chart save setup
CHART_DIR = os.path.join('charts', '10_review_anomaly')
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
print("=== gold_product_review_trust ===")
print(con.execute("DESCRIBE gold_product_review_trust").fetchdf().to_string())
print(f"\nRows: {con.execute('SELECT COUNT(*) FROM gold_product_review_trust').fetchone()[0]:,}")

print("\n=== gold_product_review_summary ===")
print(con.execute("DESCRIBE gold_product_review_summary").fetchdf().to_string())
print(f"\nRows: {con.execute('SELECT COUNT(*) FROM gold_product_review_summary').fetchone()[0]:,}")

# %% — Load & Join Trust + Summary Data
print("Loading review trust and summary data...")

df = con.execute("""
    SELECT
        t.parent_asin,
        t.source_category,
        t.review_count,
        t.unique_reviewers,
        t.reviews_per_reviewer,
        t.pct_extreme_ratings,
        t.pct_5star,
        t.pct_1star,
        t.pct_verified,
        t.pct_5star_unverified,
        t.pct_5star_verified,
        t.pct_with_text,
        t.avg_text_length,
        t.pct_very_short_text,
        t.reviews_per_day,
        t.pct_with_helpful_votes,
        -- From summary: velocity and temporal
        s.review_span_days,
        s.reviews_per_month,
        s.pct_negative
    FROM gold_product_review_trust t
    JOIN gold_product_review_summary s
        ON t.parent_asin = s.parent_asin
        AND t.source_category = s.source_category
    WHERE t.review_count >= 5
""").fetchdf()

print(f"Products with 5+ reviews: {len(df):,}")
print(f"Categories: {df['source_category'].nunique()}")

# %% — Feature Engineering
# Derived signals for anomaly detection
df['unverified_5star_gap'] = df['pct_5star_unverified'] - df['pct_5star_verified']
df['extreme_ratio'] = df['pct_extreme_ratings'] / 100  # normalize
df['text_rate'] = df['pct_with_text'] / 100
df['verified_rate'] = df['pct_verified'] / 100
df['short_text_rate'] = df['pct_very_short_text'] / 100

# Suspicious signals:
# 1. High reviews_per_day (burst patterns)
# 2. Low pct_verified (unverified flood)
# 3. High pct_extreme_ratings (polarized — could be manipulation)
# 4. Low pct_with_text (bots don't write)
# 5. High pct_very_short_text (minimal effort reviews)
# 6. High reviews_per_reviewer (repeat reviewers)
# 7. Large unverified_5star_gap (unverified inflate more than verified)
# 8. Very high pct_5star (unrealistic praise)

FEATURE_COLS = [
    'reviews_per_day',
    'verified_rate',
    'extreme_ratio',
    'text_rate',
    'short_text_rate',
    'reviews_per_reviewer',
    'unverified_5star_gap',
    'pct_5star',
    'pct_1star',
    'avg_text_length',
    'reviews_per_month',
    'pct_with_helpful_votes',
]

X = df[FEATURE_COLS].copy()

print(f"\nFeature matrix: {X.shape}")
print(f"\nNaN counts:")
print(X.isna().sum())

# Fill NaN (products with no unverified reviews have NaN gap)
X = X.fillna(0)

# Replace inf
X = X.replace([np.inf, -np.inf], 0)

print(f"\nFeature stats:")
print(X.describe().round(3).to_string())

# %% — Chart 1: Feature Distributions (Anomaly-Relevant)
key_features = ['reviews_per_day', 'verified_rate', 'pct_5star', 'short_text_rate',
                'reviews_per_reviewer', 'unverified_5star_gap']

fig = make_subplots(rows=2, cols=3, subplot_titles=key_features)
for i, col in enumerate(key_features):
    row, col_idx = i // 3 + 1, i % 3 + 1
    sample = df[col].sample(min(50000, len(df)), random_state=42)
    fig.add_trace(
        go.Histogram(x=sample, nbinsx=50, name=col, showlegend=False,
                     marker_color='#636EFA'),
        row=row, col=col_idx
    )

fig.update_layout(
    title_text="Anomaly Feature Distributions (50K sample)",
    height=500, width=1100, template='plotly_white'
)
save_chart(fig, '01_feature_distributions')
fig.show()

# %% — Scale & Fit Isolation Forest
print("Fitting Isolation Forest...")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# contamination = expected fraction of anomalies
# 5% is a reasonable starting point for review manipulation
CONTAMINATION = 0.05

iso_forest = IsolationForest(
    n_estimators=200,
    contamination=CONTAMINATION,
    random_state=42,
    n_jobs=-1
)

# Fit and predict: -1 = anomaly, 1 = normal
df['anomaly_label'] = iso_forest.fit_predict(X_scaled)

# Raw anomaly scores (lower = more anomalous)
df['anomaly_score_raw'] = iso_forest.decision_function(X_scaled)

# Convert to 0-100 trust score (higher = more trustworthy)
# decision_function: negative = anomaly, positive = normal
# Scale to 0-100 where 100 = most trustworthy
min_score = df['anomaly_score_raw'].min()
max_score = df['anomaly_score_raw'].max()
df['trust_score'] = ((df['anomaly_score_raw'] - min_score) / (max_score - min_score) * 100).round(1)

anomaly_count = (df['anomaly_label'] == -1).sum()
normal_count = (df['anomaly_label'] == 1).sum()
print(f"\nResults:")
print(f"  Normal:  {normal_count:,} ({normal_count/len(df)*100:.1f}%)")
print(f"  Anomaly: {anomaly_count:,} ({anomaly_count/len(df)*100:.1f}%)")
print(f"\nTrust score range: {df['trust_score'].min():.1f} — {df['trust_score'].max():.1f}")
print(f"Trust score mean: {df['trust_score'].mean():.1f}")
print(f"Trust score median: {df['trust_score'].median():.1f}")

# %% — Chart 2: Trust Score Distribution
fig = go.Figure()
fig.add_trace(go.Histogram(
    x=df['trust_score'], nbinsx=100,
    marker_color='#636EFA', name='All Products'
))
fig.add_vline(x=df[df['anomaly_label'] == -1]['trust_score'].max(),
              line_dash='dash', line_color='red',
              annotation_text=f'Anomaly threshold ({CONTAMINATION:.0%})')

fig.update_layout(
    title='Trust Score Distribution (0 = Suspicious, 100 = Trustworthy)',
    xaxis_title='Trust Score',
    yaxis_title='Product Count',
    template='plotly_white', width=900, height=500
)
save_chart(fig, '02_trust_score_distribution')
fig.show()

# %% — Chart 3: Anomaly vs Normal — Feature Comparison
print("\n=== Anomaly vs Normal Profiles ===\n")
comparison = df.groupby('anomaly_label')[FEATURE_COLS].mean().round(3)
comparison.index = ['Anomaly', 'Normal']
print(comparison.T.to_string())

fig = make_subplots(rows=2, cols=3,
                    subplot_titles=['Reviews/Day', 'Verified Rate', '5-Star %',
                                    'Short Text Rate', 'Reviews/Reviewer', 'Unverified 5★ Gap'])

compare_features = ['reviews_per_day', 'verified_rate', 'pct_5star',
                     'short_text_rate', 'reviews_per_reviewer', 'unverified_5star_gap']
colors = {'Normal': '#636EFA', 'Anomaly': '#EF553B'}

for i, feat in enumerate(compare_features):
    row, col_idx = i // 3 + 1, i % 3 + 1
    for label, name in [(-1, 'Anomaly'), (1, 'Normal')]:
        mask = df['anomaly_label'] == label
        sample = df.loc[mask, feat].sample(min(5000, mask.sum()), random_state=42)
        fig.add_trace(
            go.Box(y=sample, name=name, marker_color=colors[name],
                   showlegend=(i == 0)),
            row=row, col=col_idx
        )

fig.update_layout(
    title_text='Anomaly vs Normal — Feature Comparison',
    template='plotly_white', width=1100, height=600,
    boxmode='group'
)
save_chart(fig, '03_anomaly_vs_normal')
fig.show()

# %% — Chart 4: PCA Projection — Anomalies Highlighted
print("Computing PCA projection...")
pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_scaled)
print(f"Explained variance: PC1={pca.explained_variance_ratio_[0]:.1%}, PC2={pca.explained_variance_ratio_[1]:.1%}")

PLOT_SAMPLE = min(30000, len(df))
plot_idx = np.random.choice(len(df), PLOT_SAMPLE, replace=False)

# Sort so anomalies render on top
plot_df = pd.DataFrame({
    'PC1': X_pca[plot_idx, 0],
    'PC2': X_pca[plot_idx, 1],
    'Type': ['Suspicious' if l == -1 else 'Normal' for l in df['anomaly_label'].iloc[plot_idx]],
    'Trust Score': df['trust_score'].iloc[plot_idx].values
})
plot_df = plot_df.sort_values('Type', ascending=False)  # Normal first, anomalies on top

fig = px.scatter(
    plot_df, x='PC1', y='PC2', color='Type',
    color_discrete_map={'Normal': '#636EFA', 'Suspicious': '#EF553B'},
    opacity=0.4,
    labels={'PC1': f'PC1 ({pca.explained_variance_ratio_[0]:.1%})',
            'PC2': f'PC2 ({pca.explained_variance_ratio_[1]:.1%})'},
    title='PCA Projection — Suspicious Products Highlighted (30K sample)'
)
fig.update_layout(template='plotly_white', width=1000, height=700)
save_chart(fig, '04_pca_anomalies')
fig.show()

# PCA loadings
print("\nPCA Loadings:")
loadings = pd.DataFrame(
    pca.components_.T,
    columns=['PC1', 'PC2'],
    index=FEATURE_COLS
).round(3)
print(loadings.to_string())

# %% — Chart 5: Anomaly Rate by Category
cat_anomaly = df.groupby('source_category').agg(
    total=('parent_asin', 'count'),
    anomalies=('anomaly_label', lambda x: (x == -1).sum()),
    avg_trust=('trust_score', 'mean')
).reset_index()
cat_anomaly['anomaly_rate'] = (cat_anomaly['anomalies'] / cat_anomaly['total'] * 100).round(1)
cat_anomaly = cat_anomaly.sort_values('anomaly_rate', ascending=True)

fig = px.bar(
    cat_anomaly.tail(20), x='anomaly_rate', y='source_category', orientation='h',
    title='Top 20 Categories by Anomaly Rate',
    labels={'anomaly_rate': 'Anomaly Rate (%)', 'source_category': 'Category'},
    color='anomaly_rate', color_continuous_scale='Reds'
)
fig.update_layout(template='plotly_white', width=900, height=600)
save_chart(fig, '05_anomaly_rate_by_category')
fig.show()

# %% — Chart 6: Trust Score by Category
cat_trust = cat_anomaly.sort_values('avg_trust', ascending=True)

fig = px.bar(
    cat_trust, x='avg_trust', y='source_category', orientation='h',
    title='Average Trust Score by Category',
    labels={'avg_trust': 'Average Trust Score', 'source_category': 'Category'},
    color='avg_trust', color_continuous_scale='RdYlGn'
)
fig.update_layout(template='plotly_white', width=900, height=700)
save_chart(fig, '06_trust_by_category')
fig.show()

# %% — Chart 7: Top 20 Most Suspicious Products
suspicious = df[df['anomaly_label'] == -1].nsmallest(20, 'trust_score')

fig = px.bar(
    suspicious, x='trust_score',
    y=suspicious['parent_asin'] + ' (' + suspicious['source_category'].str.replace('_', ' ') + ')',
    orientation='h',
    title='Top 20 Most Suspicious Products by Trust Score',
    labels={'trust_score': 'Trust Score', 'y': 'Product (Category)'},
    color='trust_score', color_continuous_scale='Reds_r'
)
fig.update_layout(template='plotly_white', width=1000, height=650,
                  yaxis={'autorange': 'reversed'})
save_chart(fig, '07_top_suspicious_products')
fig.show()

# %% — Chart 8: Suspicious Product Feature Deviations
deviation_df = deviation.reset_index()
deviation_df.columns = ['feature', 'deviation_pct']
deviation_df = deviation_df.sort_values('deviation_pct')

fig = px.bar(
    deviation_df, x='deviation_pct', y='feature', orientation='h',
    title='Top 20 Suspicious Products — Feature Deviation from Normal (%)',
    labels={'deviation_pct': 'Deviation from Normal (%)', 'feature': 'Feature'},
    color='deviation_pct', color_continuous_scale='RdBu_r',
    color_continuous_midpoint=0
)
fig.update_layout(template='plotly_white', width=900, height=550)
save_chart(fig, '08_suspicious_deviations')
fig.show()

# %% — Chart 9: Trust Score vs Review Count
sample = df.sample(min(30000, len(df)), random_state=42)

fig = px.scatter(
    sample, x='review_count', y='trust_score',
    color='anomaly_label',
    color_discrete_map={1: '#636EFA', -1: '#EF553B'},
    opacity=0.3,
    labels={'review_count': 'Review Count', 'trust_score': 'Trust Score',
            'anomaly_label': 'Type'},
    title='Trust Score vs Review Count (30K sample)',
    log_x=True
)
fig.update_layout(template='plotly_white', width=900, height=550)
save_chart(fig, '09_trust_vs_reviews')
fig.show()

# %% — Chart 10: Trust Score Tiers
df['trust_tier'] = pd.cut(
    df['trust_score'],
    bins=[0, 20, 40, 60, 80, 100],
    labels=['Very Low (0-20)', 'Low (20-40)', 'Medium (40-60)',
            'High (60-80)', 'Very High (80-100)'],
    include_lowest=True
)

tier_counts = df['trust_tier'].value_counts().sort_index()
fig = px.bar(
    x=tier_counts.index.astype(str), y=tier_counts.values,
    text=[f"{v:,}<br>({v/len(df)*100:.1f}%)" for v in tier_counts.values],
    labels={'x': 'Trust Tier', 'y': 'Product Count'},
    title='Product Distribution by Trust Tier',
    color_discrete_sequence=['#EF553B', '#FFA15A', '#FECB52', '#00CC96', '#636EFA']
)
fig.update_traces(textposition='outside')
fig.update_layout(template='plotly_white', width=900, height=500, showlegend=False)
save_chart(fig, '10_trust_tiers')
fig.show()

# %% — Save Trust Scores to DuckDB
print("Saving trust scores to DuckDB...")

trust_output = df[['parent_asin', 'source_category', 'review_count',
                    'trust_score', 'anomaly_label',
                    'reviews_per_day', 'verified_rate', 'pct_5star',
                    'short_text_rate', 'reviews_per_reviewer',
                    'unverified_5star_gap']].copy()

trust_output['is_suspicious'] = (trust_output['anomaly_label'] == -1).astype(int)
trust_output = trust_output.drop(columns=['anomaly_label'])

con.execute("DROP TABLE IF EXISTS gold_product_trust_scores")
con.register('trust_df', trust_output)
con.execute("CREATE TABLE gold_product_trust_scores AS SELECT * FROM trust_df")

row_count = con.execute("SELECT COUNT(*) FROM gold_product_trust_scores").fetchone()[0]
print(f"gold_product_trust_scores: {row_count:,} rows saved")
print(f"\nSchema:")
print(con.execute("DESCRIBE gold_product_trust_scores").fetchdf().to_string())

suspicious_count = con.execute("SELECT COUNT(*) FROM gold_product_trust_scores WHERE is_suspicious = 1").fetchone()[0]
print(f"\nSuspicious products: {suspicious_count:,} ({suspicious_count/row_count*100:.1f}%)")

# %% — Save Model Artifacts
MODEL_DIR = os.path.join(os.path.dirname(os.getcwd()), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

model_artifacts = {
    'iso_forest': iso_forest,
    'scaler': scaler,
    'feature_cols': FEATURE_COLS,
    'contamination': CONTAMINATION,
    'pca': pca,
    'pca_loadings': loadings,
    'anomaly_threshold': df[df['anomaly_label'] == -1]['trust_score'].max(),
}

artifact_path = os.path.join(MODEL_DIR, 'review_anomaly.pkl')
with open(artifact_path, 'wb') as f:
    pickle.dump(model_artifacts, f)
print(f"Model artifacts saved: {artifact_path}")

# %% — Summary & Findings
print(f"""
╔══════════════════════════════════════════════════════════════╗
║          NB10 — REVIEW ANOMALY DETECTION SUMMARY            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Model: Isolation Forest (unsupervised)                      ║
║  Contamination: {CONTAMINATION:.0%}                                          ║
║  Products analyzed: {len(df):,}                              ║
║  Anomalies flagged: {anomaly_count:,} ({anomaly_count/len(df)*100:.1f}%)                    ║
║  Trust score range: {df['trust_score'].min():.1f} — {df['trust_score'].max():.1f}                        ║
║                                                              ║
║  Charts: 10 total                                            ║
║  Gold table: gold_product_trust_scores                       ║
║  Model artifact: models/review_anomaly.pkl                   ║
║                                                              ║
║  Findings to record:                                         ║
║  #96:  [Anomaly rate and what defines suspicious]            ║
║  #97:  [Which categories have highest anomaly rates?]        ║
║  #98:  [What distinguishes suspicious products?]             ║
║  #99:  [Trust score distribution — how many are trustworthy?]║
║  #100: [Reviews_per_day as top anomaly signal]               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

# %% — Cleanup
con.close()
print("Done. Connection closed.")
