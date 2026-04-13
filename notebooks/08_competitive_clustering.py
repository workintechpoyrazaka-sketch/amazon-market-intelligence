# %% [markdown]
# # NB08 — Competitive Clustering
# 
# **Goal:** Group Amazon products into competitive archetypes using K-Means clustering
# on category-relative features. Each product gets a cluster label that the Streamlit
# tool uses for Competitive Positioning (Q5) and Health Check (Q6-7).
#
# **Approach:** PERCENT_RANK within subcategory makes features comparable across
# categories. A $50 "cheap" electronics product and a $5 "cheap" beauty product
# both get low price_rank. Clusters become universal archetypes.

# %% — Imports & DB Connection
import os
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.decomposition import PCA

# DB path — from notebooks/ folder
DB_PATH = os.path.join(os.path.dirname(os.getcwd()), 'data', 'amazon_intelligence.duckdb')
print(f"DB: {DB_PATH}")
print(f"Exists: {os.path.exists(DB_PATH)}")

con = duckdb.connect(DB_PATH, read_only=False)
con.execute(f"SET temp_directory='{os.path.join(os.path.dirname(os.getcwd()), 'data', 'tmp')}'")

# Chart save setup
CHART_DIR = os.path.join('charts', '08_competitive_clustering')
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
print("=== silver_products ===")
print(con.execute("DESCRIBE silver_products").fetchdf().to_string())
print(f"\nRows: {con.execute('SELECT COUNT(*) FROM silver_products').fetchone()[0]:,}")

print("\n=== Active products (bought_last_month > 0) ===")
active_count = con.execute("SELECT COUNT(*) FROM silver_products WHERE bought_last_month > 0").fetchone()[0]
total_count = con.execute("SELECT COUNT(*) FROM silver_products").fetchone()[0]
print(f"Active: {active_count:,} / {total_count:,} ({active_count/total_count*100:.1f}%)")

print("\n=== Subcategory count among active ===")
sub_count = con.execute("""
    SELECT COUNT(DISTINCT subcategory) 
    FROM silver_products 
    WHERE bought_last_month > 0
""").fetchone()[0]
print(f"Subcategories with active products: {sub_count}")

# %% — Feature Extraction (SQL — category-relative percentile ranks)
print("Extracting features with category-relative percentile ranks...")

df = con.execute("""
    SELECT 
        asin,
        subcategory,
        price,
        rating,
        review_count,
        bought_last_month,
        is_best_seller,
        title_length,
        -- Category-relative ranks (0-1 scale)
        PERCENT_RANK() OVER (PARTITION BY subcategory ORDER BY price) AS price_rank,
        PERCENT_RANK() OVER (PARTITION BY subcategory ORDER BY bought_last_month) AS sales_rank,
        PERCENT_RANK() OVER (PARTITION BY subcategory ORDER BY review_count) AS reviews_rank,
        PERCENT_RANK() OVER (PARTITION BY subcategory ORDER BY title_length) AS title_length_rank
    FROM silver_products
    WHERE bought_last_month > 0
      AND price > 0
      AND rating > 0
""").fetchdf()

print(f"Products for clustering: {len(df):,}")
print(f"Subcategories: {df['subcategory'].nunique()}")
print(f"\nFeature ranges:")
for col in ['price_rank', 'sales_rank', 'reviews_rank', 'title_length_rank', 'rating']:
    print(f"  {col}: {df[col].min():.3f} — {df[col].max():.3f} (mean {df[col].mean():.3f})")

# %% — Feature Matrix
FEATURE_COLS = ['price_rank', 'sales_rank', 'reviews_rank', 'rating', 'is_best_seller', 'title_length_rank']

# is_best_seller: ensure numeric
df['is_best_seller'] = df['is_best_seller'].astype(int)

X = df[FEATURE_COLS].copy()

# Check for NaN
print("NaN counts:")
print(X.isna().sum())

# Drop any remaining NaN rows (shouldn't be many given the WHERE filters)
before = len(X)
X = X.dropna()
df = df.loc[X.index]
print(f"\nDropped {before - len(X)} NaN rows. Final: {len(X):,}")

# Scale features — StandardScaler for K-Means even though ranks are 0-1,
# because rating (1-5) and is_best_seller (0-1) have different ranges
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
print(f"\nScaled feature matrix: {X_scaled.shape}")

# %% — Chart 1: Feature Distributions
fig = make_subplots(rows=2, cols=3, subplot_titles=FEATURE_COLS)
for i, col in enumerate(FEATURE_COLS):
    row, col_idx = i // 3 + 1, i % 3 + 1
    # Sample for histogram (full dataset too heavy for plotly)
    sample = df[col].sample(min(50000, len(df)), random_state=42)
    fig.add_trace(
        go.Histogram(x=sample, nbinsx=50, name=col, showlegend=False,
                     marker_color='#636EFA'),
        row=row, col=col_idx
    )

fig.update_layout(
    title_text="Feature Distributions (50K sample)",
    height=500, width=1100,
    template='plotly_white'
)
save_chart(fig, '01_feature_distributions')
fig.show()

# %% — Chart 2: Feature Correlation Matrix
corr = df[FEATURE_COLS].corr()
fig = px.imshow(
    corr, text_auto='.2f',
    color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
    labels=dict(color='Correlation'),
    title='Feature Correlation Matrix'
)
fig.update_layout(width=700, height=600)
save_chart(fig, '02_feature_correlation')
fig.show()

# %% — Chart 3: Elbow Method (Inertia)
print("Running elbow analysis (k=2 to 12)...")
K_RANGE = range(2, 13)
inertias = []
for k in K_RANGE:
    km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
    km.fit(X_scaled)
    inertias.append(km.inertia_)
    print(f"  k={k}: inertia={km.inertia_:,.0f}")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=list(K_RANGE), y=inertias,
    mode='lines+markers', marker=dict(size=8),
    line=dict(color='#636EFA', width=2)
))
fig.update_layout(
    title='Elbow Method — Inertia vs Number of Clusters',
    xaxis_title='Number of Clusters (k)',
    yaxis_title='Inertia (within-cluster sum of squares)',
    template='plotly_white',
    width=900, height=500
)
save_chart(fig, '03_elbow_curve')
fig.show()

# %% — Chart 4: Silhouette Scores
print("Computing silhouette scores (k=2 to 10)...")
# Silhouette on full dataset can be slow — sample if needed
SILHOUETTE_SAMPLE = min(50000, len(X_scaled))
np.random.seed(42)
sil_idx = np.random.choice(len(X_scaled), SILHOUETTE_SAMPLE, replace=False)
X_sil = X_scaled[sil_idx]

sil_scores = []
for k in range(2, 11):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_sil)
    score = silhouette_score(X_sil, labels)
    sil_scores.append(score)
    print(f"  k={k}: silhouette={score:.4f}")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=list(range(2, 11)), y=sil_scores,
    mode='lines+markers', marker=dict(size=8),
    line=dict(color='#EF553B', width=2)
))
fig.update_layout(
    title='Silhouette Score vs Number of Clusters',
    xaxis_title='Number of Clusters (k)',
    yaxis_title='Silhouette Score (higher = better separation)',
    template='plotly_white',
    width=900, height=500
)
save_chart(fig, '04_silhouette_scores')
fig.show()

# %% — Select Optimal k & Fit Final Model
# DECISION: Pick k based on elbow + silhouette + business interpretability.
# Look at the charts above. Typical sweet spot is 4-6.
# Adjust OPTIMAL_K here after reviewing:

OPTIMAL_K = 5  # <-- ADJUST after reviewing elbow + silhouette charts

print(f"\nFitting final K-Means with k={OPTIMAL_K}...")
kmeans = KMeans(n_clusters=OPTIMAL_K, random_state=42, n_init=20, max_iter=500)
df['cluster'] = kmeans.fit_predict(X_scaled)

print(f"\nCluster sizes:")
cluster_sizes = df['cluster'].value_counts().sort_index()
for c, count in cluster_sizes.items():
    print(f"  Cluster {c}: {count:,} products ({count/len(df)*100:.1f}%)")

#%%print("\n=== Cluster Profiles (mean values) ===\n")
profile_cols = ['price', 'rating', 'review_count', 'bought_last_month', 'is_best_seller',
                'price_rank', 'sales_rank', 'reviews_rank', 'title_length_rank']

profiles = df.groupby('cluster')[profile_cols].agg(['mean', 'median']).round(2)
print(profiles.to_string())

# Simpler view — means only
print("\n=== Simplified Profiles (means) ===\n")
simple_profiles = df.groupby('cluster')[FEATURE_COLS].mean().round(3)
print(simple_profiles.to_string())

# Revenue per cluster
print("\n=== Revenue by Cluster ===\n")
df['estimated_revenue'] = df['price'] * df['bought_last_month']
rev_by_cluster = df.groupby('cluster').agg(
    products=('asin', 'count'),
    total_revenue=('estimated_revenue', 'sum'),
    avg_revenue=('estimated_revenue', 'mean'),
    median_revenue=('estimated_revenue', 'median'),
    avg_price=('price', 'mean'),
    avg_sales=('bought_last_month', 'mean'),
    avg_rating=('rating', 'mean'),
    avg_reviews=('review_count', 'mean'),
    pct_bestseller=('is_best_seller', 'mean')
).round(2)
rev_by_cluster['total_revenue_M'] = (rev_by_cluster['total_revenue'] / 1e6).round(1)
rev_by_cluster['pct_bestseller'] = (rev_by_cluster['pct_bestseller'] * 100).round(1)
print(rev_by_cluster.to_string())

# %% — Name the Clusters
# Based on the profiles above, assign business-meaningful names.
# ADJUST these after reviewing the profile output:

CLUSTER_NAMES = {
    0: "Silent Volume Movers",
    1: "Struggling Listers",
    2: "Review-Rich Veterans",
    3: "Quiet Quality",
    4: "Best Seller Elite",
}
# Example names (common archetypes that emerge):
# "Premium Leaders" — high price_rank, high sales_rank, high reviews, often bestSeller
# "Budget Volume Players" — low price_rank, high sales_rank, many reviews
# "Niche Stars" — mid-high price, moderate sales, excellent ratings
# "Mid-Pack Competitors" — average everything, the crowded middle
# "Struggling Tail" — low sales, low reviews, undifferentiated

df['cluster_name'] = df['cluster'].map(CLUSTER_NAMES)

# %% — Chart 5: Cluster Size Distribution
fig = px.bar(
    x=[CLUSTER_NAMES.get(i, f"Cluster {i}") for i in cluster_sizes.index],
    y=cluster_sizes.values,
    text=[f"{v:,}<br>({v/len(df)*100:.1f}%)" for v in cluster_sizes.values],
    labels={'x': 'Cluster', 'y': 'Product Count'},
    title=f'Cluster Size Distribution (k={OPTIMAL_K})',
    color_discrete_sequence=['#636EFA']
)
fig.update_traces(textposition='outside')
fig.update_layout(template='plotly_white', width=900, height=500, showlegend=False)
save_chart(fig, '05_cluster_sizes')
fig.show()

# %% — Chart 6: Radar Chart — Cluster Profiles
# Normalize means to 0-1 for radar comparison
radar_data = df.groupby('cluster')[FEATURE_COLS].mean()
# Min-max scale across clusters for visual comparison
radar_norm = (radar_data - radar_data.min()) / (radar_data.max() - radar_data.min())

fig = go.Figure()
colors = px.colors.qualitative.Set2[:OPTIMAL_K]
for cluster_id in range(OPTIMAL_K):
    values = radar_norm.loc[cluster_id].tolist()
    values.append(values[0])  # close the polygon
    categories = FEATURE_COLS + [FEATURE_COLS[0]]
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=CLUSTER_NAMES.get(cluster_id, f"Cluster {cluster_id}"),
        opacity=0.6,
        line=dict(color=colors[cluster_id])
    ))

fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    title=f'Cluster Profiles — Radar Comparison (k={OPTIMAL_K})',
    template='plotly_white',
    width=900, height=600
)
save_chart(fig, '06_cluster_radar')
fig.show()

# %% — Chart 7: Revenue by Cluster
fig = make_subplots(rows=1, cols=2, subplot_titles=['Total Revenue ($M)', 'Avg Revenue per Product ($)'])

fig.add_trace(
    go.Bar(x=[CLUSTER_NAMES.get(i, f"C{i}") for i in rev_by_cluster.index],
           y=rev_by_cluster['total_revenue_M'],
           marker_color=colors[:OPTIMAL_K],
           showlegend=False),
    row=1, col=1
)
fig.add_trace(
    go.Bar(x=[CLUSTER_NAMES.get(i, f"C{i}") for i in rev_by_cluster.index],
           y=rev_by_cluster['avg_revenue'],
           marker_color=colors[:OPTIMAL_K],
           showlegend=False),
    row=1, col=2
)

fig.update_layout(
    title_text='Revenue Distribution by Cluster',
    template='plotly_white', width=1100, height=500
)
save_chart(fig, '07_revenue_by_cluster')
fig.show()

# %% — Chart 8: PCA 2D Projection
print("Computing PCA projection (2D)...")
pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_scaled)
print(f"Explained variance: PC1={pca.explained_variance_ratio_[0]:.1%}, PC2={pca.explained_variance_ratio_[1]:.1%}")
print(f"Total: {sum(pca.explained_variance_ratio_):.1%}")

# Sample for plotting (full scatter is too heavy)
PLOT_SAMPLE = min(30000, len(df))
plot_idx = np.random.choice(len(df), PLOT_SAMPLE, replace=False)

fig = px.scatter(
    x=X_pca[plot_idx, 0], y=X_pca[plot_idx, 1],
    color=[CLUSTER_NAMES.get(c, f"Cluster {c}") for c in df['cluster'].iloc[plot_idx]],
    labels={'x': f'PC1 ({pca.explained_variance_ratio_[0]:.1%})',
            'y': f'PC2 ({pca.explained_variance_ratio_[1]:.1%})'},
    title=f'PCA Projection — Product Clusters (30K sample)',
    opacity=0.4,
    color_discrete_sequence=colors
)
fig.update_layout(template='plotly_white', width=1000, height=700)
save_chart(fig, '08_pca_projection')
fig.show()

# PCA loadings — what each PC means
print("\nPCA Loadings (feature contributions to each PC):")
loadings = pd.DataFrame(
    pca.components_.T,
    columns=['PC1', 'PC2'],
    index=FEATURE_COLS
).round(3)
print(loadings.to_string())

# %% — Chart 9: Cluster × Top Subcategories Heatmap
# Which clusters dominate which categories?
top_subcats = df['subcategory'].value_counts().head(20).index.tolist()
cluster_subcat = df[df['subcategory'].isin(top_subcats)].groupby(
    ['subcategory', 'cluster']
).size().unstack(fill_value=0)

# Normalize to percentages within each subcategory
cluster_subcat_pct = cluster_subcat.div(cluster_subcat.sum(axis=1), axis=0) * 100

fig = px.imshow(
    cluster_subcat_pct.round(1),
    text_auto='.0f',
    labels=dict(x='Cluster', y='Subcategory', color='% of Products'),
    title='Cluster Composition by Top 20 Subcategories',
    color_continuous_scale='Blues',
    aspect='auto'
)
fig.update_xaxes(tickvals=list(range(OPTIMAL_K)),
                 ticktext=[CLUSTER_NAMES.get(i, f"C{i}") for i in range(OPTIMAL_K)])
fig.update_layout(width=900, height=700, template='plotly_white')
save_chart(fig, '09_cluster_subcategory_heatmap')
fig.show()

# %% — Chart 10: Box Plots — Key Metrics by Cluster
fig = make_subplots(rows=2, cols=2,
                    subplot_titles=['Price ($)', 'Monthly Sales', 'Rating (Stars)', 'Review Count'])

# Sample for box plots
box_sample = df.sample(min(30000, len(df)), random_state=42)

for i, (col, title) in enumerate([
    ('price', 'Price'), ('bought_last_month', 'Sales'),
    ('rating', 'Rating'), ('review_count', 'Reviews')
]):
    row, col_idx = i // 2 + 1, i % 2 + 1
    for cluster_id in range(OPTIMAL_K):
        mask = box_sample['cluster'] == cluster_id
        fig.add_trace(
            go.Box(y=box_sample.loc[mask, col],
                   name=CLUSTER_NAMES.get(cluster_id, f"C{cluster_id}"),
                   marker_color=colors[cluster_id],
                   showlegend=(i == 0)),
            row=row, col=col_idx
        )

# Cap outliers visually
fig.update_yaxes(range=[0, box_sample['price'].quantile(0.95)], row=1, col=1)
fig.update_yaxes(range=[0, box_sample['bought_last_month'].quantile(0.95)], row=1, col=2)
fig.update_yaxes(range=[0, 5.5], row=2, col=1)
fig.update_yaxes(range=[0, box_sample['review_count'].quantile(0.95)], row=2, col=2)

fig.update_layout(
    title_text='Product Metrics by Cluster',
    template='plotly_white', width=1100, height=700,
    boxmode='group'
)
save_chart(fig, '10_metrics_by_cluster')
fig.show()

# %% — Save Cluster Assignments to DuckDB
print("Saving cluster assignments to DuckDB...")

# Create a DataFrame with just asin + cluster + cluster_name
cluster_output = df[['asin', 'subcategory', 'cluster', 'cluster_name',
                      'price_rank', 'sales_rank', 'reviews_rank']].copy()

# Register as temp table and write to Gold
con.execute("DROP TABLE IF EXISTS gold_product_clusters")
con.register('cluster_df', cluster_output)
con.execute("""
    CREATE TABLE gold_product_clusters AS 
    SELECT * FROM cluster_df
""")

row_count = con.execute("SELECT COUNT(*) FROM gold_product_clusters").fetchone()[0]
print(f"gold_product_clusters: {row_count:,} rows saved")
print(f"\nSchema:")
print(con.execute("DESCRIBE gold_product_clusters").fetchdf().to_string())

# Verify
print(f"\nCluster distribution in DuckDB:")
print(con.execute("""
    SELECT cluster, cluster_name, COUNT(*) as products 
    FROM gold_product_clusters 
    GROUP BY cluster, cluster_name 
    ORDER BY cluster
""").fetchdf().to_string())

# %% — Save K-Means Model Artifacts
import pickle

MODEL_DIR = os.path.join(os.path.dirname(os.getcwd()), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

model_artifacts = {
    'kmeans': kmeans,
    'scaler': scaler,
    'feature_cols': FEATURE_COLS,
    'cluster_names': CLUSTER_NAMES,
    'optimal_k': OPTIMAL_K,
    'pca': pca,
    'pca_loadings': loadings,
}

artifact_path = os.path.join(MODEL_DIR, 'competitive_clusters.pkl')
with open(artifact_path, 'wb') as f:
    pickle.dump(model_artifacts, f)
print(f"Model artifacts saved: {artifact_path}")

# %% — Summary & Findings
print("""
╔══════════════════════════════════════════════════════════════╗
║              NB08 — COMPETITIVE CLUSTERING SUMMARY          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Review the output above and fill in:                        ║
║                                                              ║
║  1. OPTIMAL_K — adjust based on elbow + silhouette charts    ║
║  2. CLUSTER_NAMES — name each cluster from its profile       ║
║  3. Re-run from "Select Optimal k" cell onward               ║
║                                                              ║
║  Findings to record (fill after naming clusters):            ║
║  #83: [Optimal k value and why]                              ║
║  #84: [Largest cluster — what archetype dominates?]          ║
║  #85: [Revenue concentration — which cluster earns most?]   ║
║  #86: [Best seller distribution across clusters]            ║
║  #87: [Cluster × category patterns]                         ║
║  #88: [PCA explained variance — feature redundancy?]        ║
║                                                              ║
║  Charts: 10 total                                            ║
║  Gold table: gold_product_clusters                           ║
║  Model artifact: models/competitive_clusters.pkl             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

# %% — Cleanup
con.close()
print("Done. Connection closed.")
