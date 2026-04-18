"""
Amazon Market Intelligence — Streamlit App
5 modes × 11 customer questions
All queries hit pre-aggregated Gold tables in DuckDB.
"""

import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import json

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Amazon Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# DuckDB path — relative from app/ to data/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "amazon_intelligence.duckdb"
PARQUET_DIR = PROJECT_ROOT / "data" / "parquet"


@st.cache_resource
def get_connection():
    """
    Connect to DuckDB.
    - If local .duckdb file exists: use it directly (read-only).
    - Otherwise: load Parquet files into in-memory DuckDB (Streamlit Cloud).
    """
    if DB_PATH.exists():
        return duckdb.connect(str(DB_PATH), read_only=True)

    # Cloud mode — load Parquet into memory
    conn = duckdb.connect(":memory:")
    for pq_file in sorted(PARQUET_DIR.glob("*.parquet")):
        table_name = pq_file.stem
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{pq_file}')")
    return conn


@st.cache_data(ttl=3600)
def run_query(sql: str) -> pd.DataFrame:
    """Run SQL against Gold tables, return DataFrame. Cached 1 hour."""
    conn = get_connection()
    return conn.execute(sql).fetchdf()


# ─────────────────────────────────────────────
# SHARED STYLES
# ─────────────────────────────────────────────

def metric_row(cols_data: list[tuple[str, str, str | None]]):
    """Display a row of st.metric cards. Each tuple: (label, value, delta)."""
    cols = st.columns(len(cols_data))
    for col, (label, value, delta) in zip(cols, cols_data):
        col.metric(label, value, delta)


def format_currency(val, decimals=0):
    if val >= 1_000_000_000:
        return f"${val / 1_000_000_000:,.{decimals}f}B"
    if val >= 1_000_000:
        return f"${val / 1_000_000:,.{decimals}f}M"
    if val >= 1_000:
        return f"${val / 1_000:,.{decimals}f}K"
    return f"${val:,.{decimals}f}"


def format_number(val, decimals=0):
    if val >= 1_000_000:
        return f"{val / 1_000_000:,.{decimals}f}M"
    if val >= 1_000:
        return f"{val / 1_000:,.{decimals}f}K"
    return f"{val:,.{decimals}f}"


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.title("📊 Amazon Intelligence")
    st.caption("What actually drives success on Amazon?")
    st.divider()

    mode = st.radio(
        "Tool Mode",
        [
            "🔍 Category Scout",
            "⚔️ Competitive Positioning",
            "🩺 Health Check",
            "💬 Voice of Customer",
            "🛡️ Review Trust Score",
        ],
        index=0,
    )

    st.divider()
    st.caption("Data: 1.4M products · 526M reviews · 248 subcategories")
    st.caption("Built by Poi — 2026")


# ─────────────────────────────────────────────
# MODE 1: CATEGORY SCOUT
# ─────────────────────────────────────────────

def category_scout():
    st.header("🔍 Category Scout")
    st.markdown("**Where should I sell? Is my category growing or dying? How competitive is my space?**")

    # ── Zoom level toggle ──
    zoom = st.radio(
        "Zoom Level",
        ["Subcategory (248 — full revenue data)", "Main Category (50 — full ecosystem)"],
        horizontal=True,
    )

    if zoom.startswith("Subcategory"):
        _category_scout_subcategory()
    else:
        _category_scout_main_category()


def _category_scout_subcategory():
    """Subcategory-level Category Scout — 248 subcategories with full revenue."""

    df = run_query("SELECT * FROM gold_subcategory_landscape ORDER BY total_revenue DESC")

    # ── Top-level metrics ──
    metric_row([
        ("Total Revenue", format_currency(df["total_revenue"].sum()), None),
        ("Products", format_number(df["product_count"].sum()), None),
        ("Subcategories", str(len(df)), None),
        ("Avg Rating", f"{df['avg_rating'].mean():.2f}", None),
    ])

    st.divider()

    # ── Opportunity Scoring ──
    # Composite score: high revenue/product + high activity + low competition (fewer products)
    # Normalize each factor 0-1 within dataset
    scored = df.copy()
    for col in ["avg_revenue_per_product", "pct_active", "total_revenue"]:
        min_v, max_v = scored[col].min(), scored[col].max()
        scored[f"{col}_norm"] = (scored[col] - min_v) / (max_v - min_v + 1e-9)

    # Competition inverse: fewer products = less competition = higher score
    scored["competition_norm"] = 1 - (
        (scored["product_count"] - scored["product_count"].min())
        / (scored["product_count"].max() - scored["product_count"].min() + 1e-9)
    )

    scored["opportunity_score"] = (
        scored["avg_revenue_per_product_norm"] * 0.35
        + scored["pct_active_norm"] * 0.25
        + scored["total_revenue_norm"] * 0.20
        + scored["competition_norm"] * 0.20
    ) * 100

    scored = scored.sort_values("opportunity_score", ascending=False)

    # ── Filters ──
    col1, col2, col3 = st.columns(3)
    with col1:
        min_revenue = st.select_slider(
            "Min Total Revenue",
            options=[0, 1_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000],
            format_func=lambda x: format_currency(x),
            value=0,
        )
    with col2:
        min_products = st.number_input("Min Products", min_value=0, value=0, step=100)
    with col3:
        top_n = st.slider("Show Top N", min_value=10, max_value=248, value=30, step=10)

    filtered = scored[
        (scored["total_revenue"] >= min_revenue)
        & (scored["product_count"] >= min_products)
    ].head(top_n)

    # ── Opportunity Ranking Chart ──
    st.subheader("Category Opportunity Ranking")

    fig = px.bar(
        filtered.head(20),
        x="opportunity_score",
        y="subcategory",
        orientation="h",
        color="opportunity_score",
        color_continuous_scale="Viridis",
        labels={"opportunity_score": "Opportunity Score", "subcategory": ""},
    )
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        height=600,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Revenue vs Competition Scatter ──
    st.subheader("Revenue Potential vs Competition")

    fig2 = px.scatter(
        filtered,
        x="product_count",
        y="avg_revenue_per_product",
        size="total_revenue",
        color="pct_active",
        hover_name="subcategory",
        labels={
            "product_count": "Products (Competition)",
            "avg_revenue_per_product": "Revenue per Product ($)",
            "pct_active": "% Active",
            "total_revenue": "Total Revenue",
        },
        color_continuous_scale="RdYlGn",
    )
    fig2.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

    # ── Detail Table ──
    st.subheader("Category Details")

    display_cols = [
        "subcategory", "opportunity_score", "product_count", "total_revenue",
        "avg_revenue_per_product", "avg_price", "avg_rating", "pct_active",
        "pct_best_sellers", "avg_discount_pct",
    ]

    st.dataframe(
        filtered[display_cols].style.format({
            "opportunity_score": "{:.1f}",
            "total_revenue": "${:,.0f}",
            "avg_revenue_per_product": "${:,.0f}",
            "avg_price": "${:.2f}",
            "avg_rating": "{:.2f}",
            "pct_active": "{:.1f}%",
            "pct_best_sellers": "{:.2f}%",
            "avg_discount_pct": "{:.1f}%",
        }),
        use_container_width=True,
        height=400,
    )

    # ── Temporal Trends for selected category ──
    st.divider()
    st.subheader("📈 Category Growth Trend")
    st.markdown("*Is this category growing or dying? Select a category to see its review volume and rating trajectory.*")

    # Get available categories from temporal trends
    trend_categories = run_query(
        "SELECT DISTINCT source_category FROM gold_temporal_trends ORDER BY source_category"
    )["source_category"].tolist()

    selected_cat = st.selectbox("Select category for trend analysis", trend_categories)

    if selected_cat:
        trend_df = run_query(f"""
            SELECT review_year, review_month, review_count, avg_rating, pct_verified, pct_negative
            FROM gold_temporal_trends
            WHERE source_category = '{selected_cat}'
              AND review_year >= 2015
            ORDER BY review_year, review_month
        """)

        if len(trend_df) > 0:
            trend_df["date"] = pd.to_datetime(
                trend_df["review_year"].astype(str) + "-" + trend_df["review_month"].astype(str).str.zfill(2) + "-01"
            )

            fig3 = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                subplot_titles=("Monthly Review Volume", "Average Rating Over Time"),
            )

            fig3.add_trace(
                go.Bar(x=trend_df["date"], y=trend_df["review_count"], name="Reviews", marker_color="#636EFA"),
                row=1, col=1,
            )

            fig3.add_trace(
                go.Scatter(x=trend_df["date"], y=trend_df["avg_rating"], name="Avg Rating",
                           mode="lines+markers", marker=dict(size=4), line=dict(color="#EF553B")),
                row=2, col=1,
            )

            fig3.update_layout(height=500, showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
            fig3.update_yaxes(title_text="Reviews", row=1, col=1)
            fig3.update_yaxes(title_text="Rating", row=2, col=1)
            st.plotly_chart(fig3, use_container_width=True)

            # Growth summary
            recent = trend_df[trend_df["review_year"] >= 2021]
            older = trend_df[(trend_df["review_year"] >= 2018) & (trend_df["review_year"] <= 2020)]

            if len(recent) > 0 and len(older) > 0:
                vol_change = (recent["review_count"].mean() / older["review_count"].mean() - 1) * 100
                rating_change = recent["avg_rating"].mean() - older["avg_rating"].mean()

                c1, c2 = st.columns(2)
                c1.metric(
                    "Volume Change (2021+ vs 2018-20)",
                    f"{vol_change:+.1f}%",
                    "Growing" if vol_change > 0 else "Declining",
                )
                c2.metric(
                    "Rating Shift",
                    f"{rating_change:+.3f}",
                    "Improving" if rating_change > 0 else "Declining",
                )


def _category_scout_main_category():
    """Main category level — 50 categories, full ecosystem view."""

    df = run_query("SELECT * FROM gold_main_category_landscape ORDER BY total_revenue DESC")

    metric_row([
        ("Ecosystem Products", format_number(df["ecosystem_products"].sum()), None),
        ("Stores", format_number(df["store_count"].sum()), None),
        ("Brands", format_number(df["brand_count"].sum()), None),
        ("Main Categories", str(len(df)), None),
    ])

    st.divider()

    # ── Revenue Treemap ──
    st.subheader("Revenue by Main Category")

    top20 = df.head(20)
    fig = px.treemap(
        top20,
        path=["main_category"],
        values="total_revenue",
        color="avg_revenue_per_product",
        color_continuous_scale="Viridis",
        labels={"avg_revenue_per_product": "Rev/Product"},
    )
    fig.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # ── Ecosystem Density ──
    st.subheader("Ecosystem Density: Products per Store")

    fig2 = px.scatter(
        df.fillna({"total_revenue": 0}),
        x="store_count",
        y="ecosystem_products",
        size="total_revenue",
        color="products_per_store",
        hover_name="main_category",
        color_continuous_scale="RdYlGn_r",
        labels={
            "store_count": "Stores",
            "ecosystem_products": "Products",
            "products_per_store": "Products/Store",
        },
    )
    fig2.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

    # ── Table ──
    st.subheader("All Main Categories")
    display_cols = [
        "main_category", "ecosystem_products", "store_count", "brand_count",
        "total_revenue", "avg_revenue_per_product", "avg_price", "avg_rating",
        "pct_active", "products_per_store",
    ]
    st.dataframe(
        df[display_cols].style.format({
            "ecosystem_products": "{:,.0f}",
            "store_count": "{:,.0f}",
            "brand_count": "{:,.0f}",
            "total_revenue": "${:,.0f}",
            "avg_revenue_per_product": "${:,.0f}",
            "avg_price": "${:.2f}",
            "avg_rating": "{:.2f}",
            "pct_active": "{:.1f}%",
            "products_per_store": "{:.1f}",
        }),
        use_container_width=True,
        height=500,
    )


# ─────────────────────────────────────────────
# MODE 2: COMPETITIVE POSITIONING
# ─────────────────────────────────────────────

def competitive_positioning():
    st.header("⚔️ Competitive Positioning")
    st.markdown("**What's the price sweet spot? Who are my competitors and how do they win?**")

    # ── Category selector ──
    categories = run_query(
        "SELECT DISTINCT subcategory FROM gold_price_positioning ORDER BY subcategory"
    )["subcategory"].tolist()

    selected = st.selectbox("Select subcategory", categories, index=None, placeholder="Choose a subcategory...")

    if not selected:
        st.info("Select a subcategory above to see its competitive landscape.")
        return

    st.divider()

    # ── Load all data for this category ──
    df_price = run_query(f"""
        SELECT * FROM gold_price_positioning
        WHERE subcategory = '{selected.replace("'", "''")}'
        ORDER BY CASE price_tier
            WHEN 'Budget' THEN 1 WHEN 'Low' THEN 2 WHEN 'Mid' THEN 3
            WHEN 'Premium' THEN 4 WHEN 'Luxury' THEN 5 ELSE 6 END
    """)

    df_brand = run_query(f"""
        SELECT * FROM gold_brand_dynamics
        WHERE subcategory = '{selected.replace("'", "''")}'
    """)

    df_disc = run_query(f"""
        SELECT * FROM gold_discount_effectiveness
        WHERE subcategory = '{selected.replace("'", "''")}'
        ORDER BY CASE discount_tier
            WHEN 'No Discount' THEN 1 WHEN 'Light (1-19%)' THEN 2
            WHEN 'Medium (20-49%)' THEN 3 WHEN 'Deep (50%+)' THEN 4 ELSE 5 END
    """)

    df_clusters = run_query(f"""
        SELECT cluster_name, COUNT(*) as product_count,
               AVG(price_rank) as avg_price_rank,
               AVG(sales_rank) as avg_sales_rank,
               AVG(reviews_rank) as avg_reviews_rank
        FROM gold_product_clusters
        WHERE subcategory = '{selected.replace("'", "''")}'
        GROUP BY cluster_name
        ORDER BY product_count DESC
    """)

    df_listing = run_query(f"""
        SELECT * FROM gold_listing_quality
        WHERE subcategory = '{selected.replace("'", "''")}'
    """)

    # ── Top-level metrics ──
    total_products = df_price["product_count"].sum()
    total_revenue = df_price["total_revenue"].sum()
    weighted_rating = (df_price["avg_rating"] * df_price["product_count"]).sum() / max(total_products, 1)

    # Find winning tier
    if len(df_price) > 0:
        winner = df_price.loc[df_price["avg_revenue_per_product"].idxmax()]
        winning_tier = winner["price_tier"]
    else:
        winning_tier = "N/A"

    metric_row([
        ("Products", format_number(total_products), None),
        ("Total Revenue", format_currency(total_revenue), None),
        ("Avg Rating", f"{weighted_rating:.2f}", None),
        ("Best Tier (Rev/Product)", winning_tier, None),
    ])

    st.divider()

    # ────────────────────────────────────────
    # PRICE SWEET SPOT
    # ────────────────────────────────────────
    st.subheader("💰 Price Sweet Spot")

    if len(df_price) > 0:
        col1, col2 = st.columns(2)

        with col1:
            # Revenue per product by tier
            fig_rev = px.bar(
                df_price,
                x="price_tier",
                y="avg_revenue_per_product",
                color="price_tier",
                text="avg_revenue_per_product",
                labels={"avg_revenue_per_product": "Revenue per Product ($)", "price_tier": ""},
                title="Revenue per Product by Price Tier",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_rev.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            fig_rev.update_layout(height=400, showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_rev, width="stretch")

        with col2:
            # Total revenue by tier
            fig_total = px.bar(
                df_price,
                x="price_tier",
                y="total_revenue",
                color="price_tier",
                text="total_revenue",
                labels={"total_revenue": "Total Revenue ($)", "price_tier": ""},
                title="Total Revenue by Price Tier",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_total.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            fig_total.update_layout(height=400, showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_total, width="stretch")

        # Detail table
        price_display = df_price[[
            "price_tier", "product_count", "avg_price", "avg_revenue_per_product",
            "total_revenue", "avg_rating", "pct_active", "pct_best_sellers",
        ]].copy()
        price_display.columns = ["Tier", "Products", "Avg Price", "Rev/Product", "Total Rev", "Rating", "% Active", "% Best Sellers"]
        st.dataframe(
            price_display.style.format({
                "Avg Price": "${:.2f}", "Rev/Product": "${:,.0f}", "Total Rev": "${:,.0f}",
                "Rating": "{:.2f}", "% Active": "{:.1f}%", "% Best Sellers": "{:.2f}%",
            }),
            width="stretch", hide_index=True,
        )
    else:
        st.warning("No price positioning data for this subcategory.")

    st.divider()

    # ────────────────────────────────────────
    # BRAND vs UNBRANDED
    # ────────────────────────────────────────
    st.subheader("🏷️ Brand vs Unbranded")

    if len(df_brand) > 0:
        col1, col2 = st.columns(2)

        with col1:
            fig_brand_rev = px.bar(
                df_brand,
                x="brand_status",
                y="avg_revenue_per_product",
                color="brand_status",
                text="avg_revenue_per_product",
                labels={"avg_revenue_per_product": "Revenue per Product ($)", "brand_status": ""},
                title="Revenue per Product",
                color_discrete_map={"Branded": "#636EFA", "Unbranded": "#EF553B"},
            )
            fig_brand_rev.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            fig_brand_rev.update_layout(height=350, showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_brand_rev, width="stretch")

        with col2:
            fig_brand_share = px.pie(
                df_brand,
                values="total_revenue",
                names="brand_status",
                title="Revenue Share",
                color="brand_status",
                color_discrete_map={"Branded": "#636EFA", "Unbranded": "#EF553B"},
            )
            fig_brand_share.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_brand_share, width="stretch")

        # Brand multiplier
        branded = df_brand[df_brand["brand_status"] == "Branded"]
        unbranded = df_brand[df_brand["brand_status"] == "Unbranded"]
        if len(branded) > 0 and len(unbranded) > 0:
            b_rev = branded["avg_revenue_per_product"].iloc[0]
            u_rev = unbranded["avg_revenue_per_product"].iloc[0]
            if u_rev > 0:
                multiplier = b_rev / u_rev
                st.metric("Brand Multiplier", f"{multiplier:.1f}×",
                          "Brand advantage" if multiplier > 1 else "Unbranded wins")
            elif b_rev > 0:
                st.metric("Brand Multiplier", "∞", "Unbranded has zero revenue")
    else:
        st.warning("No brand dynamics data for this subcategory.")

    st.divider()

    # ────────────────────────────────────────
    # DISCOUNT EFFECTIVENESS
    # ────────────────────────────────────────
    st.subheader("🏷️ Discount Effectiveness")

    if len(df_disc) > 0:
        fig_disc = px.bar(
            df_disc,
            x="discount_tier",
            y="avg_revenue_per_product",
            color="discount_tier",
            text="avg_revenue_per_product",
            labels={"avg_revenue_per_product": "Revenue per Product ($)", "discount_tier": ""},
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_disc.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig_disc.update_layout(height=400, showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_disc, width="stretch")

        disc_display = df_disc[[
            "discount_tier", "product_count", "avg_discount", "avg_revenue_per_product",
            "total_revenue", "pct_active",
        ]].copy()
        disc_display.columns = ["Tier", "Products", "Avg Discount", "Rev/Product", "Total Rev", "% Active"]
        st.dataframe(
            disc_display.style.format({
                "Avg Discount": "{:.1f}%", "Rev/Product": "${:,.0f}",
                "Total Rev": "${:,.0f}", "% Active": "{:.1f}%",
            }),
            width="stretch", hide_index=True,
        )
    else:
        st.warning("No discount data for this subcategory.")

    st.divider()

    # ────────────────────────────────────────
    # COMPETITIVE CLUSTERS
    # ────────────────────────────────────────
    st.subheader("🎯 Competitive Landscape (Clusters)")

    if len(df_clusters) > 0:
        # Cluster distribution pie
        col1, col2 = st.columns(2)

        with col1:
            fig_clust = px.pie(
                df_clusters,
                values="product_count",
                names="cluster_name",
                title="Product Distribution by Archetype",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_clust.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_clust, width="stretch")

        with col2:
            # Radar-style comparison using bar
            cluster_metrics = df_clusters.melt(
                id_vars=["cluster_name"],
                value_vars=["avg_price_rank", "avg_sales_rank", "avg_reviews_rank"],
                var_name="metric",
                value_name="avg_rank",
            )
            cluster_metrics["metric"] = cluster_metrics["metric"].map({
                "avg_price_rank": "Price Position",
                "avg_sales_rank": "Sales Position",
                "avg_reviews_rank": "Review Position",
            })

            fig_profile = px.bar(
                cluster_metrics,
                x="metric",
                y="avg_rank",
                color="cluster_name",
                barmode="group",
                title="Archetype Profiles (higher = stronger)",
                labels={"avg_rank": "Avg Percentile Rank", "metric": "", "cluster_name": "Archetype"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_profile.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_profile, width="stretch")

        # Cluster summary table
        st.dataframe(
            df_clusters.style.format({
                "product_count": "{:,.0f}",
                "avg_price_rank": "{:.2f}",
                "avg_sales_rank": "{:.2f}",
                "avg_reviews_rank": "{:.2f}",
            }),
            width="stretch", hide_index=True,
        )
    else:
        st.warning("No cluster data for this subcategory.")

    st.divider()

    # ────────────────────────────────────────
    # LISTING QUALITY IMPACT
    # ────────────────────────────────────────
    st.subheader("📝 Listing Quality Impact")

    if len(df_listing) > 0:
        row = df_listing.iloc[0]

        # Build comparison pairs
        pairs = []
        for element, with_col, without_col, label in [
            ("Features", "avg_rev_with_features", "avg_rev_without_features", "Has Features"),
            ("Description", "avg_rev_with_description", "avg_rev_without_description", "Has Description"),
            ("Brand", "avg_rev_with_brand", "avg_rev_without_brand", "Has Brand"),
        ]:
            if with_col in row.index and without_col in row.index:
                w = row[with_col] if pd.notna(row[with_col]) else 0
                wo = row[without_col] if pd.notna(row[without_col]) else 0
                pairs.append({"Element": element, "With": w, "Without": wo})

        if pairs:
            pairs_df = pd.DataFrame(pairs)
            pairs_df["Lift"] = pairs_df.apply(
                lambda r: (r["With"] / r["Without"] - 1) * 100 if r["Without"] > 0 else 0, axis=1
            )

            fig_listing = go.Figure()
            fig_listing.add_trace(go.Bar(
                name="With Element", x=pairs_df["Element"], y=pairs_df["With"],
                marker_color="#636EFA", text=pairs_df["With"].apply(lambda v: f"${v:,.0f}"),
                textposition="outside",
            ))
            fig_listing.add_trace(go.Bar(
                name="Without Element", x=pairs_df["Element"], y=pairs_df["Without"],
                marker_color="#EF553B", text=pairs_df["Without"].apply(lambda v: f"${v:,.0f}"),
                textposition="outside",
            ))
            fig_listing.update_layout(
                barmode="group", height=400, title="Avg Revenue: With vs Without Listing Elements",
                yaxis_title="Avg Revenue per Product ($)", margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig_listing, width="stretch")

            # Completeness score
            if "avg_completeness_score" in row.index and pd.notna(row["avg_completeness_score"]):
                col1, col2 = st.columns(2)
                col1.metric("Avg Listing Completeness", f"{row['avg_completeness_score']:.1f}%")
                if "pct_with_features" in row.index:
                    col2.metric("% With Features Listed", f"{row['pct_with_features']:.1f}%")
    else:
        st.warning("No listing quality data for this subcategory.")


# ─────────────────────────────────────────────
# MODE 3: HEALTH CHECK
# ─────────────────────────────────────────────

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


@st.cache_resource
def load_ml_artifacts():
    """Load XGBoost model + feature names from success_factors.pkl."""
    try:
        import joblib
        artifacts = joblib.load(MODELS_DIR / "success_factors.pkl")
        return artifacts
    except Exception as e:
        return {"error": str(e)}


def health_check():
    st.header("🩺 Health Check")
    st.markdown("**How does my product compare? What am I doing wrong? Am I about to get disrupted?**")

    # ── ASIN input ──
    asin_input = st.text_input(
        "Enter product ASIN",
        placeholder="e.g. B08N5WRWNW",
        help="The Amazon Standard Identification Number for your product",
    )

    if not asin_input:
        st.info("Enter a product ASIN above to run a full health check.")
        return

    asin = asin_input.strip().upper()

    # ── Look up product ──
    product = run_query(f"""
        SELECT * FROM silver_products WHERE asin = '{asin}'
    """)

    if len(product) == 0:
        st.error(f"ASIN **{asin}** not found in the database (1.4M Kaggle products).")
        return

    p = product.iloc[0]
    subcategory = p["subcategory"]

    st.divider()

    # ── Product Summary ──
    st.subheader(f"📦 {p.get('title', asin)[:80]}")

    metric_row([
        ("Price", f"${p['price']:.2f}" if pd.notna(p["price"]) else "N/A", None),
        ("Rating", f"{p['rating']:.1f}" if pd.notna(p["rating"]) else "N/A", None),
        ("Reviews", format_number(p["review_count"]) if pd.notna(p["review_count"]) else "0", None),
        ("Monthly Sales", format_number(p["bought_last_month"]) if pd.notna(p["bought_last_month"]) else "0", None),
    ])

    col1, col2, col3 = st.columns(3)
    col1.metric("Subcategory", subcategory)
    col2.metric("Best Seller", "✅ Yes" if p.get("is_best_seller") else "❌ No")
    est_rev = p.get("estimated_revenue", 0) or 0
    col3.metric("Est. Revenue", format_currency(est_rev))

    st.divider()

    # ────────────────────────────────────────
    # CATEGORY BENCHMARKING
    # ────────────────────────────────────────
    st.subheader("📊 How You Compare to Your Category")

    bench = run_query(f"""
        SELECT * FROM gold_subcategory_landscape
        WHERE subcategory = '{subcategory.replace("'", "''")}'
    """)

    if len(bench) > 0:
        b = bench.iloc[0]

        # Compute percentile ranks within subcategory
        percentiles = run_query(f"""
            SELECT
                PERCENT_RANK() OVER (ORDER BY price) as price_pctile,
                PERCENT_RANK() OVER (ORDER BY rating) as rating_pctile,
                PERCENT_RANK() OVER (ORDER BY review_count) as reviews_pctile,
                PERCENT_RANK() OVER (ORDER BY bought_last_month) as sales_pctile,
                PERCENT_RANK() OVER (ORDER BY estimated_revenue) as revenue_pctile
            FROM silver_products
            WHERE subcategory = '{subcategory.replace("'", "''")}'
            QUALIFY asin = '{asin}'
        """)

        if len(percentiles) > 0:
            pctl = percentiles.iloc[0]

            # Radar chart
            categories_radar = ["Price", "Rating", "Reviews", "Sales", "Revenue"]
            values = [
                pctl["price_pctile"] * 100,
                pctl["rating_pctile"] * 100,
                pctl["reviews_pctile"] * 100,
                pctl["sales_pctile"] * 100,
                pctl["revenue_pctile"] * 100,
            ]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories_radar + [categories_radar[0]],
                fill="toself",
                name="Your Product",
                fillcolor="rgba(99, 110, 250, 0.3)",
                line=dict(color="#636EFA"),
            ))
            # 50th percentile reference
            fig_radar.add_trace(go.Scatterpolar(
                r=[50] * 6,
                theta=categories_radar + [categories_radar[0]],
                name="Category Median",
                line=dict(color="#EF553B", dash="dash"),
            ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                height=450,
                margin=dict(l=60, r=60, t=30, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_radar, width="stretch")

            # Percentile summary
            metric_row([
                ("Price Percentile", f"{pctl['price_pctile']*100:.0f}th", None),
                ("Rating Percentile", f"{pctl['rating_pctile']*100:.0f}th", None),
                ("Reviews Percentile", f"{pctl['reviews_pctile']*100:.0f}th", None),
                ("Revenue Percentile", f"{pctl['revenue_pctile']*100:.0f}th", None),
            ])

        # Category averages comparison table
        st.markdown("**Your Product vs Category Averages**")
        compare_data = []
        for label, prod_val, cat_val, fmt in [
            ("Price", p.get("price"), b.get("avg_price"), "${:.2f}"),
            ("Rating", p.get("rating"), b.get("avg_rating"), "{:.2f}"),
            ("Reviews", p.get("review_count"), b.get("avg_reviews"), "{:,.0f}"),
            ("Revenue/Product", est_rev, b.get("avg_revenue_per_product"), "${:,.0f}"),
        ]:
            pv = prod_val if pd.notna(prod_val) else 0
            cv = cat_val if pd.notna(cat_val) else 0
            diff = ((pv / cv - 1) * 100) if cv > 0 else 0
            compare_data.append({
                "Metric": label,
                "Your Product": fmt.format(pv),
                "Category Avg": fmt.format(cv),
                "Difference": f"{diff:+.1f}%",
            })

        st.dataframe(pd.DataFrame(compare_data), width="stretch", hide_index=True)

    st.divider()

    # ────────────────────────────────────────
    # CLUSTER ASSIGNMENT
    # ────────────────────────────────────────
    st.subheader("🎯 Your Competitive Archetype")

    cluster = run_query(f"""
        SELECT cluster_name, cluster, price_rank, sales_rank, reviews_rank
        FROM gold_product_clusters
        WHERE asin = '{asin}'
    """)

    if len(cluster) > 0:
        cl = cluster.iloc[0]

        archetype_descriptions = {
            "Silent Volume Movers": "High sales with minimal reviews. You sell without social proof — focus on maintaining volume.",
            "Struggling Listers": "Low sales and engagement. Consider repricing, improving listing quality, or pivoting category.",
            "Review-Rich Veterans": "Strong review base but moderate sales. Social proof isn't converting — check pricing and relevance.",
            "Quiet Quality": "Decent ratings but low visibility. You need more reviews and possibly advertising to grow.",
            "Best Seller Elite": "Top performers with badge, reviews, and sales. Defend your position — watch for disruptors.",
        }

        st.success(f"**{cl['cluster_name']}**")
        desc = archetype_descriptions.get(cl["cluster_name"], "")
        if desc:
            st.markdown(desc)

        metric_row([
            ("Price Rank", f"{cl['price_rank']:.2f}", None),
            ("Sales Rank", f"{cl['sales_rank']:.2f}", None),
            ("Reviews Rank", f"{cl['reviews_rank']:.2f}", None),
        ])

        # Show cluster distribution in this subcategory
        cluster_dist = run_query(f"""
            SELECT cluster_name, COUNT(*) as count
            FROM gold_product_clusters
            WHERE subcategory = '{subcategory.replace("'", "''")}'
            GROUP BY cluster_name
            ORDER BY count DESC
        """)

        if len(cluster_dist) > 0:
            fig_clust = px.pie(
                cluster_dist,
                values="count",
                names="cluster_name",
                title=f"Competitive Landscape in {subcategory}",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_clust.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_clust, width="stretch")
    else:
        st.info("No cluster assignment found for this product.")

    st.divider()

    # ────────────────────────────────────────
    # ML DIAGNOSIS — SHAP WATERFALL
    # ────────────────────────────────────────
    st.subheader("🧠 ML Diagnosis — What Drives Your Success Score?")

    ml = load_ml_artifacts()

    if "error" in ml:
        st.warning(f"ML model not available: {ml['error']}")
        st.info("Install xgboost, shap, and joblib to enable ML diagnosis.")
        return

    try:
        import shap

        model = ml["model"]
        feature_cols = ml["feature_cols"]
        shap_expected = ml["shap_expected_value"]

        # Build feature vector — SQL differs between local DuckDB and Parquet mode
        # Parquet has pre-computed columns; local DuckDB needs computation
        use_parquet = not DB_PATH.exists()

        if use_parquet:
            feature_sql = f"""
                SELECT
                    price, rating, review_count, title_length,
                    CAST(is_best_seller AS INTEGER) as is_best_seller,
                    has_brand, has_features, has_description, has_store,
                    discount_pct, is_mcauley_matched,
                    PERCENT_RANK() OVER (ORDER BY price) as price_rank,
                    PERCENT_RANK() OVER (ORDER BY review_count) as reviews_rank,
                    PERCENT_RANK() OVER (ORDER BY title_length) as title_length_rank
                FROM silver_products
                WHERE subcategory = '{subcategory.replace("'", "''")}'
                QUALIFY asin = '{asin}'
            """
        else:
            feature_sql = f"""
                SELECT
                    price, rating, review_count,
                    LENGTH(title) as title_length,
                    CAST(is_best_seller AS INTEGER) as is_best_seller,
                    CASE WHEN brand IS NOT NULL AND brand != '' THEN 1 ELSE 0 END as has_brand,
                    CASE WHEN features IS NOT NULL AND features != '' THEN 1 ELSE 0 END as has_features,
                    CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END as has_description,
                    CASE WHEN store IS NOT NULL AND store != '' THEN 1 ELSE 0 END as has_store,
                    COALESCE(discount_pct, 0) as discount_pct,
                    CASE WHEN main_category IS NOT NULL THEN 1 ELSE 0 END as is_mcauley_matched,
                    PERCENT_RANK() OVER (ORDER BY price) as price_rank,
                    PERCENT_RANK() OVER (ORDER BY review_count) as reviews_rank,
                    PERCENT_RANK() OVER (ORDER BY LENGTH(title)) as title_length_rank
                FROM silver_products
                WHERE subcategory = '{subcategory.replace("'", "''")}'
                QUALIFY asin = '{asin}'
            """

        feature_df = run_query(feature_sql)

        if len(feature_df) == 0:
            st.warning("Could not compute features for this product.")
            return

        X = feature_df[feature_cols].values.astype(float)

        # Handle NaN — fill with 0 for missing values
        X = np.nan_to_num(X, nan=0.0)

        # Run SHAP
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        if isinstance(shap_values, list):
            sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
        elif len(shap_values.shape) > 1:
            sv = shap_values[0]
        else:
            sv = shap_values

        # Build waterfall data
        shap_df = pd.DataFrame({
            "Feature": feature_cols,
            "SHAP Value": sv,
            "Abs SHAP": np.abs(sv),
        }).sort_values("Abs SHAP", ascending=True)

        base_value = shap_expected
        if isinstance(base_value, (list, np.ndarray)):
            base_value = float(base_value[1]) if len(base_value) > 1 else float(base_value[0])

        # Get prediction
        prediction = model.predict_proba(X)[0]
        success_prob = prediction[1] if len(prediction) > 1 else prediction[0]

        # Waterfall chart
        fig_shap = go.Figure(go.Waterfall(
            orientation="h",
            y=shap_df["Feature"],
            x=shap_df["SHAP Value"],
            connector=dict(line=dict(color="rgba(0,0,0,0)")),
            increasing=dict(marker=dict(color="#00CC96")),
            decreasing=dict(marker=dict(color="#EF553B")),
            textposition="outside",
            text=[f"{v:+.3f}" for v in shap_df["SHAP Value"]],
        ))

        fig_shap.update_layout(
            title=f"SHAP: What's helping and hurting (prediction: {success_prob:.0%})",
            height=max(400, len(feature_cols) * 35),
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis_title="Impact on Success Prediction",
        )
        st.plotly_chart(fig_shap, width="stretch")

        # Interpretation
        top_positive = shap_df[shap_df["SHAP Value"] > 0].tail(3)
        top_negative = shap_df[shap_df["SHAP Value"] < 0].head(3)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**✅ Helping you:**")
            for _, row in top_positive.iterrows():
                st.markdown(f"- **{row['Feature']}**: {row['SHAP Value']:+.3f}")
        with col2:
            st.markdown("**❌ Hurting you:**")
            for _, row in top_negative.iterrows():
                st.markdown(f"- **{row['Feature']}**: {row['SHAP Value']:+.3f}")

        # Success probability
        success_pct = success_prob * 100
        if success_pct >= 60:
            st.success(f"**Success probability: {success_pct:.0f}%** — This product is well-positioned.")
        elif success_pct >= 40:
            st.warning(f"**Success probability: {success_pct:.0f}%** — Room for improvement. Focus on the red factors above.")
        else:
            st.error(f"**Success probability: {success_pct:.0f}%** — Significant challenges. Consider the recommendations above.")

    except Exception as e:
        st.warning(f"ML diagnosis encountered an error: {e}")
        st.info("The benchmarking and cluster analysis above still provide actionable insights.")

    except Exception as e:
        st.warning(f"ML diagnosis encountered an error: {e}")
        st.info("The benchmarking and cluster analysis above still provide actionable insights.")


# ─────────────────────────────────────────────
# MODE 4: VOICE OF CUSTOMER
# ─────────────────────────────────────────────

def voice_of_customer():
    st.header("💬 Voice of Customer")
    st.markdown("**What are customers actually saying?**")

    # ── Category selector (source_category = 33 main categories) ──
    categories = run_query(
        "SELECT DISTINCT source_category FROM gold_review_sentiment ORDER BY source_category"
    )["source_category"].tolist()

    selected = st.selectbox("Select category", categories, index=None, placeholder="Choose a category...")

    if not selected:
        st.info("Select a category above to see what customers are saying.")
        return

    st.divider()

    # ── Load data ──
    df_sent = run_query(f"""
        SELECT * FROM gold_review_sentiment
        WHERE source_category = '{selected.replace("'", "''")}'
    """)

    df_kw_neg = run_query(f"""
        SELECT word, word_count FROM gold_review_keywords
        WHERE source_category = '{selected.replace("'", "''")}'
          AND sentiment = 'negative'
        ORDER BY word_count DESC
        LIMIT 20
    """)

    df_kw_pos = run_query(f"""
        SELECT word, word_count FROM gold_review_keywords
        WHERE source_category = '{selected.replace("'", "''")}'
          AND sentiment = 'positive'
        ORDER BY word_count DESC
        LIMIT 20
    """)

    df_trend = run_query(f"""
        SELECT review_year, review_month, review_count, avg_rating,
               pct_negative, negative_reviews, positive_reviews, neutral_reviews
        FROM gold_temporal_trends
        WHERE source_category = '{selected.replace("'", "''")}'
          AND review_year >= 2015
        ORDER BY review_year, review_month
    """)

    if len(df_sent) == 0:
        st.warning("No sentiment data for this category.")
        return

    row = df_sent.iloc[0]

    # ── Top-level metrics ──
    metric_row([
        ("Total Reviews", format_number(row["total_reviews"]), None),
        ("Avg Rating", f"{row['avg_rating']:.2f}", None),
        ("% Negative", f"{row['pct_negative']:.1f}%", None),
        ("% Positive", f"{row['pct_positive']:.1f}%", None),
    ])

    st.divider()

    # ────────────────────────────────────────
    # SENTIMENT SPLIT
    # ────────────────────────────────────────
    st.subheader("📊 Sentiment Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        sent_data = pd.DataFrame({
            "Sentiment": ["Positive", "Neutral", "Negative"],
            "Count": [row["positive_count"], row["neutral_count"], row["negative_count"]],
            "Percentage": [row["pct_positive"], row["pct_neutral"], row["pct_negative"]],
        })

        fig_pie = px.pie(
            sent_data,
            values="Count",
            names="Sentiment",
            color="Sentiment",
            color_discrete_map={"Positive": "#00CC96", "Neutral": "#FFA15A", "Negative": "#EF553B"},
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pie, width="stretch")

    with col2:
        # Review characteristics
        chars = []
        chars.append({"Metric": "Reviews with Text", "Value": f"{row['pct_with_text']:.1f}%"})
        chars.append({"Metric": "Avg Text Length (all)", "Value": f"{row['avg_text_length']:.0f} chars"})
        chars.append({"Metric": "Avg Text Length (negative)", "Value": f"{row['avg_text_length_negative']:.0f} chars"})
        chars.append({"Metric": "Avg Text Length (positive)", "Value": f"{row['avg_text_length_positive']:.0f} chars"})
        chars.append({"Metric": "Negative Verbosity Ratio", "Value": f"{row['negative_verbosity_ratio']:.2f}×"})
        chars.append({"Metric": "Avg Helpful Votes (negative)", "Value": f"{row['avg_helpful_negative']:.2f}"})
        chars.append({"Metric": "Avg Helpful Votes (positive)", "Value": f"{row['avg_helpful_positive']:.2f}"})
        chars.append({"Metric": "% Images (negative)", "Value": f"{row['pct_images_negative']:.1f}%"})
        chars.append({"Metric": "% Images (positive)", "Value": f"{row['pct_images_positive']:.1f}%"})

        st.dataframe(pd.DataFrame(chars), width="stretch", hide_index=True, height=350)

    st.divider()

    # ────────────────────────────────────────
    # COMPLAINT KEYWORDS
    # ────────────────────────────────────────
    st.subheader("🔴 Top Complaint Keywords")

    if len(df_kw_neg) > 0:
        fig_neg = px.bar(
            df_kw_neg.iloc[:15],
            x="word_count",
            y="word",
            orientation="h",
            labels={"word_count": "Frequency in Negative Reviews", "word": ""},
            color_discrete_sequence=["#EF553B"],
        )
        fig_neg.update_layout(
            yaxis=dict(autorange="reversed"),
            height=450,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig_neg, width="stretch")
    else:
        st.info("No complaint keywords for this category.")

    # ────────────────────────────────────────
    # PRAISE KEYWORDS
    # ────────────────────────────────────────
    st.subheader("🟢 Top Praise Keywords")

    if len(df_kw_pos) > 0:
        fig_pos = px.bar(
            df_kw_pos.iloc[:15],
            x="word_count",
            y="word",
            orientation="h",
            labels={"word_count": "Frequency in Positive Reviews", "word": ""},
            color_discrete_sequence=["#00CC96"],
        )
        fig_pos.update_layout(
            yaxis=dict(autorange="reversed"),
            height=450,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig_pos, width="stretch")
    else:
        st.info("No praise keywords for this category.")

    st.divider()

    # ────────────────────────────────────────
    # SENTIMENT OVER TIME
    # ────────────────────────────────────────
    st.subheader("📈 Sentiment Trends Over Time")

    if len(df_trend) > 0:
        df_trend["date"] = pd.to_datetime(
            df_trend["review_year"].astype(str) + "-"
            + df_trend["review_month"].astype(str).str.zfill(2) + "-01"
        )

        fig_trend = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("Monthly Review Volume", "% Negative Reviews Over Time"),
        )

        fig_trend.add_trace(
            go.Bar(x=df_trend["date"], y=df_trend["review_count"],
                   name="Reviews", marker_color="#636EFA"),
            row=1, col=1,
        )

        fig_trend.add_trace(
            go.Scatter(x=df_trend["date"], y=df_trend["pct_negative"],
                       name="% Negative", mode="lines+markers",
                       marker=dict(size=3), line=dict(color="#EF553B")),
            row=2, col=1,
        )

        fig_trend.update_layout(height=500, showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
        fig_trend.update_yaxes(title_text="Reviews", row=1, col=1)
        fig_trend.update_yaxes(title_text="% Negative", row=2, col=1)
        st.plotly_chart(fig_trend, width="stretch")
    else:
        st.info("No temporal trend data for this category.")


# ─────────────────────────────────────────────
# MODE 5: REVIEW TRUST SCORE
# ─────────────────────────────────────────────

def review_trust_score():
    st.header("🛡️ Review Trust Score")
    st.markdown("**Can I trust these reviews?**")

    # ── View toggle ──
    view = st.radio(
        "View",
        ["Category Overview", "Suspicious Products"],
        horizontal=True,
    )

    if view == "Category Overview":
        _review_trust_category()
    else:
        _review_trust_products()


def _review_trust_category():
    """Category-level review trust signals."""

    df = run_query("SELECT * FROM gold_review_trust ORDER BY pct_verified ASC")

    # ── Top-level metrics ──
    total_reviews = df["total_reviews"].sum()
    avg_verified = (df["pct_verified"] * df["total_reviews"]).sum() / max(total_reviews, 1)
    avg_extreme = (df["pct_extreme_ratings"] * df["total_reviews"]).sum() / max(total_reviews, 1)

    metric_row([
        ("Total Reviews", format_number(total_reviews), None),
        ("Avg Verified Rate", f"{avg_verified:.1f}%", None),
        ("Avg Extreme Ratings", f"{avg_extreme:.1f}%", None),
        ("Categories", str(len(df)), None),
    ])

    st.divider()

    # ── Verified Rate by Category ──
    st.subheader("🔍 Verified Purchase Rate by Category")

    fig_ver = px.bar(
        df.sort_values("pct_verified"),
        x="pct_verified",
        y="source_category",
        orientation="h",
        color="pct_verified",
        color_continuous_scale="RdYlGn",
        labels={"pct_verified": "% Verified", "source_category": ""},
    )
    fig_ver.update_layout(
        yaxis=dict(autorange="reversed"),
        height=700,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_ver, width="stretch")

    st.divider()

    # ── Unverified 5-Star Gap ──
    st.subheader("⚠️ Unverified vs Verified 5-Star Rate")
    st.markdown("*When unverified reviewers give MORE 5-stars than verified buyers, it may signal manipulation.*")

    df["unverified_5star_gap"] = df["pct_5star_among_unverified"] - df["pct_5star_among_verified"]

    fig_gap = px.bar(
        df.sort_values("unverified_5star_gap", ascending=False),
        x="unverified_5star_gap",
        y="source_category",
        orientation="h",
        color="unverified_5star_gap",
        color_continuous_scale="RdYlGn_r",
        labels={"unverified_5star_gap": "Gap (Unverified − Verified)", "source_category": ""},
    )
    fig_gap.update_layout(
        yaxis=dict(autorange="reversed"),
        height=700,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_gap, width="stretch")

    st.divider()

    # ── Rating Distribution ──
    st.subheader("📊 Rating Distribution by Category")

    selected_cat = st.selectbox(
        "Select category for rating breakdown",
        df["source_category"].tolist(),
        index=None,
        placeholder="Choose a category...",
    )

    if selected_cat:
        cat_row = df[df["source_category"] == selected_cat].iloc[0]
        dist_data = pd.DataFrame({
            "Rating": ["5-Star", "4-Star", "3-Star", "2-Star", "1-Star"],
            "Percentage": [
                cat_row["pct_5star"], cat_row["pct_4star"], cat_row["pct_3star"],
                cat_row["pct_2star"], cat_row["pct_1star"],
            ],
        })

        fig_dist = px.bar(
            dist_data,
            x="Rating",
            y="Percentage",
            color="Rating",
            color_discrete_map={
                "5-Star": "#00CC96", "4-Star": "#636EFA", "3-Star": "#FFA15A",
                "2-Star": "#FF6692", "1-Star": "#EF553B",
            },
            text="Percentage",
        )
        fig_dist.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_dist.update_layout(height=350, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_dist, width="stretch")

        # Key stats
        metric_row([
            ("Verified Rate", f"{cat_row['pct_verified']:.1f}%", None),
            ("Extreme Ratings", f"{cat_row['pct_extreme_ratings']:.1f}%", None),
            ("Reviews/Reviewer", f"{cat_row['reviews_per_reviewer']:.2f}", None),
            ("% With Text", f"{cat_row['pct_with_text']:.1f}%", None),
        ])

    st.divider()

    # ── Full table ──
    st.subheader("All Categories")
    display_cols = [
        "source_category", "total_reviews", "unique_reviewers", "pct_verified",
        "pct_extreme_ratings", "reviews_per_reviewer", "pct_5star",
        "pct_5star_among_unverified", "pct_5star_among_verified",
    ]
    st.dataframe(
        df[display_cols].style.format({
            "total_reviews": "{:,.0f}", "unique_reviewers": "{:,.0f}",
            "pct_verified": "{:.1f}%", "pct_extreme_ratings": "{:.1f}%",
            "reviews_per_reviewer": "{:.2f}", "pct_5star": "{:.1f}%",
            "pct_5star_among_unverified": "{:.1f}%", "pct_5star_among_verified": "{:.1f}%",
        }),
        width="stretch", hide_index=True, height=500,
    )


def _review_trust_products():
    """Product-level suspicious review detection."""

    # ── Category filter ──
    categories = run_query(
        "SELECT DISTINCT source_category FROM gold_product_trust_scores ORDER BY source_category"
    )["source_category"].tolist()

    selected = st.selectbox("Filter by category", ["All Categories"] + categories)

    where = ""
    if selected != "All Categories":
        where = f"WHERE source_category = '{selected.replace(chr(39), chr(39)*2)}'"

    # ── Summary stats ──
    stats = run_query(f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_suspicious THEN 1 ELSE 0 END) as suspicious_count,
            AVG(trust_score) as avg_trust,
            AVG(CASE WHEN is_suspicious THEN trust_score END) as avg_trust_suspicious,
            AVG(CASE WHEN NOT is_suspicious THEN trust_score END) as avg_trust_normal
        FROM gold_product_trust_scores
        {where}
    """).iloc[0]

    pct_sus = stats["suspicious_count"] / max(stats["total"], 1) * 100

    metric_row([
        ("Products Analyzed", format_number(stats["total"]), None),
        ("Flagged Suspicious", format_number(stats["suspicious_count"]), f"{pct_sus:.1f}%"),
        ("Avg Trust Score (normal)", f"{stats['avg_trust_normal']:.2f}", None),
        ("Avg Trust Score (suspicious)", f"{stats['avg_trust_suspicious']:.2f}", None),
    ])

    st.divider()

    # ── Trust Score Distribution ──
    st.subheader("📊 Trust Score Distribution")

    df_hist = run_query(f"""
        SELECT trust_score, is_suspicious FROM gold_product_trust_scores
        {where}
    """)

    fig_hist = px.histogram(
        df_hist,
        x="trust_score",
        color="is_suspicious",
        nbins=50,
        color_discrete_map={True: "#EF553B", False: "#00CC96"},
        labels={"trust_score": "Trust Score", "is_suspicious": "Suspicious"},
        barmode="overlay",
        opacity=0.7,
    )
    fig_hist.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_hist, width="stretch")

    st.divider()

    # ── Suspicious vs Normal Comparison ──
    st.subheader("🔬 Suspicious vs Normal Product Profiles")

    comparison = run_query(f"""
        SELECT
            CASE WHEN is_suspicious THEN 'Suspicious' ELSE 'Normal' END as group_label,
            COUNT(*) as products,
            AVG(review_count) as avg_reviews,
            AVG(reviews_per_day) as avg_velocity,
            AVG(verified_rate) * 100 as avg_verified_pct,
            AVG(pct_5star) as avg_5star,
            AVG(short_text_rate) * 100 as avg_short_text_pct,
            AVG(reviews_per_reviewer) as avg_reviews_per_reviewer,
            AVG(unverified_5star_gap) as avg_unverified_gap
        FROM gold_product_trust_scores
        {where}
        GROUP BY CASE WHEN is_suspicious THEN 'Suspicious' ELSE 'Normal' END
    """)

    if len(comparison) == 2:
        metrics_to_plot = [
            ("avg_velocity", "Review Velocity (per day)"),
            ("avg_verified_pct", "Verified Rate (%)"),
            ("avg_5star", "5-Star Rate (%)"),
            ("avg_short_text_pct", "Short Text Rate (%)"),
            ("avg_reviews_per_reviewer", "Reviews per Reviewer"),
        ]

        melted = comparison.melt(
            id_vars=["group_label"],
            value_vars=[m[0] for m in metrics_to_plot],
            var_name="metric",
            value_name="value",
        )
        melted["metric"] = melted["metric"].map(dict(metrics_to_plot))

        fig_comp = px.bar(
            melted,
            x="metric",
            y="value",
            color="group_label",
            barmode="group",
            color_discrete_map={"Normal": "#00CC96", "Suspicious": "#EF553B"},
            labels={"value": "", "metric": "", "group_label": ""},
        )
        fig_comp.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_comp, width="stretch")

    st.divider()

    # ── Most Suspicious Products ──
    st.subheader("🚨 Most Suspicious Products")

    top_suspicious = run_query(f"""
        SELECT parent_asin, source_category, review_count, trust_score,
               reviews_per_day, verified_rate, pct_5star,
               short_text_rate, unverified_5star_gap
        FROM gold_product_trust_scores
        {where}
        {'AND' if where else 'WHERE'} is_suspicious = true
        ORDER BY trust_score ASC
        LIMIT 50
    """)

    if len(top_suspicious) > 0:
        st.dataframe(
            top_suspicious.style.format({
                "trust_score": "{:.3f}", "reviews_per_day": "{:.3f}",
                "verified_rate": "{:.1%}", "pct_5star": "{:.1f}%",
                "short_text_rate": "{:.1%}", "unverified_5star_gap": "{:.1f}",
            }),
            width="stretch", hide_index=True, height=500,
        )
    else:
        st.info("No suspicious products found with current filters.")


# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────

MODE_MAP = {
    "🔍 Category Scout": category_scout,
    "⚔️ Competitive Positioning": competitive_positioning,
    "🩺 Health Check": health_check,
    "💬 Voice of Customer": voice_of_customer,
    "🛡️ Review Trust Score": review_trust_score,
}

MODE_MAP[mode]()
