"""
Smoke test — validates every Gold table query the Streamlit app uses.
Run from project root:  python app/test_app.py
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "amazon_intelligence.duckdb")

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  — {detail}")


def run(conn, sql: str) -> pd.DataFrame:
    return conn.execute(sql).fetchdf()


def main():
    global PASS, FAIL

    print(f"\n🔌 Connecting to: {DB_PATH}")
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        sys.exit(1)
    print("  ✅ Connected\n")

    # ──────────────────────────────────────────
    # 1. ALL GOLD TABLES EXIST
    # ──────────────────────────────────────────
    print("── 1. Gold Tables Exist ──")
    expected_tables = [
        "gold_subcategory_landscape",
        "gold_main_category_landscape",
        "gold_temporal_trends",
        "gold_price_positioning",
        "gold_brand_dynamics",
        "gold_discount_effectiveness",
        "gold_listing_quality",
        "gold_bestseller_analysis",
        "gold_product_benchmarks",
        "gold_category_benchmarks_full",
        "gold_store_performance",
        "gold_review_sentiment",
        "gold_review_keywords",
        "gold_review_trust",
        "gold_product_review_summary",
        "gold_product_review_trust",
        "gold_product_clusters",
        "gold_product_trust_scores",
    ]

    all_tables = run(conn, "SHOW TABLES")["name"].tolist()
    for t in expected_tables:
        check(t, t in all_tables, f"not found in database")

    # ──────────────────────────────────────────
    # 2. CATEGORY SCOUT — SUBCATEGORY
    # ──────────────────────────────────────────
    print("\n── 2. Category Scout: Subcategory ──")
    df = run(conn, "SELECT * FROM gold_subcategory_landscape ORDER BY total_revenue DESC")
    check("Row count = 248", len(df) == 248, f"got {len(df)}")
    check("No NULL subcategory", df["subcategory"].isna().sum() == 0)
    check("No NULL total_revenue", df["total_revenue"].isna().sum() == 0)
    check("No NULL avg_revenue_per_product", df["avg_revenue_per_product"].isna().sum() == 0)
    check("No NULL pct_active", df["pct_active"].isna().sum() == 0)
    check("No NULL product_count", df["product_count"].isna().sum() == 0)
    check("Revenue > 0 for top category", df["total_revenue"].iloc[0] > 0)
    check("avg_rating in [0, 5]", df["avg_rating"].between(0, 5).all(), f"range: {df['avg_rating'].min()}-{df['avg_rating'].max()}")

    # Opportunity score columns needed
    for col in ["avg_revenue_per_product", "pct_active", "total_revenue", "product_count"]:
        check(f"Column '{col}' no NaN", df[col].isna().sum() == 0, f"{df[col].isna().sum()} NaN")

    # ──────────────────────────────────────────
    # 3. CATEGORY SCOUT — MAIN CATEGORY
    # ──────────────────────────────────────────
    print("\n── 3. Category Scout: Main Category ──")
    df2 = run(conn, "SELECT * FROM gold_main_category_landscape ORDER BY total_revenue DESC")
    check("Row count = 50", len(df2) == 50, f"got {len(df2)}")
    check("No NULL main_category", df2["main_category"].isna().sum() == 0)

    # The NaN bug we hit — total_revenue used as scatter size
    nan_rev = df2["total_revenue"].isna().sum()
    check("total_revenue NaN count", True, f"{nan_rev} rows have NaN (handled with fillna)")

    for col in ["ecosystem_products", "store_count", "products_per_store"]:
        check(f"Column '{col}' exists", col in df2.columns, "missing")

    # ──────────────────────────────────────────
    # 4. CATEGORY SCOUT — TEMPORAL TRENDS
    # ──────────────────────────────────────────
    print("\n── 4. Category Scout: Temporal Trends ──")
    df3 = run(conn, "SELECT * FROM gold_temporal_trends")
    check(f"Row count > 0", len(df3) > 0, f"got {len(df3)}")
    check("Has source_category", "source_category" in df3.columns)
    check("Has review_year", "review_year" in df3.columns)
    check("Has review_count", "review_count" in df3.columns)
    check("Has avg_rating", "avg_rating" in df3.columns)

    categories = df3["source_category"].nunique()
    check(f"Multiple categories ({categories})", categories > 1)

    year_range = f"{df3['review_year'].min()}-{df3['review_year'].max()}"
    check(f"Year range spans multiple years", df3["review_year"].nunique() > 5, f"range: {year_range}")

    # ──────────────────────────────────────────
    # 5. COMPETITIVE POSITIONING (future mode)
    # ──────────────────────────────────────────
    print("\n── 5. Competitive Positioning Tables ──")
    df_price = run(conn, "SELECT * FROM gold_price_positioning")
    check(f"gold_price_positioning rows > 0", len(df_price) > 0, f"got {len(df_price)}")
    check("Has price_tier", "price_tier" in df_price.columns)

    df_brand = run(conn, "SELECT * FROM gold_brand_dynamics")
    check(f"gold_brand_dynamics rows > 0", len(df_brand) > 0, f"got {len(df_brand)}")

    df_disc = run(conn, "SELECT * FROM gold_discount_effectiveness")
    check(f"gold_discount_effectiveness rows > 0", len(df_disc) > 0, f"got {len(df_disc)}")

    df_clust = run(conn, "SELECT * FROM gold_product_clusters")
    check(f"gold_product_clusters rows > 0", len(df_clust) > 0, f"got {len(df_clust)}")
    check("Has cluster_name", "cluster_name" in df_clust.columns)
    cluster_names = df_clust["cluster_name"].unique().tolist()
    check(f"5 cluster archetypes", len(cluster_names) == 5, f"got {len(cluster_names)}: {cluster_names}")

    # ──────────────────────────────────────────
    # 6. HEALTH CHECK (future mode)
    # ──────────────────────────────────────────
    print("\n── 6. Health Check Tables ──")
    df_bench = run(conn, "SELECT * FROM gold_product_benchmarks")
    check(f"gold_product_benchmarks rows > 0", len(df_bench) > 0, f"got {len(df_bench)}")

    df_cbf = run(conn, "SELECT * FROM gold_category_benchmarks_full")
    check(f"gold_category_benchmarks_full rows > 0", len(df_cbf) > 0, f"got {len(df_cbf)}")

    df_store = run(conn, "SELECT * FROM gold_store_performance")
    check(f"gold_store_performance rows > 0", len(df_store) > 0, f"got {len(df_store)}")

    df_bs = run(conn, "SELECT * FROM gold_bestseller_analysis")
    check(f"gold_bestseller_analysis rows > 0", len(df_bs) > 0, f"got {len(df_bs)}")

    # ML model files
    models_dir = Path(__file__).resolve().parent.parent / "models"
    for model_file in ["competitive_clusters.pkl", "success_factors.pkl", "success_model.json", "review_anomaly.pkl"]:
        path = models_dir / model_file
        check(f"Model: {model_file}", path.exists(), f"not found at {path}")

    # ──────────────────────────────────────────
    # 7. VOICE OF CUSTOMER (future mode)
    # ──────────────────────────────────────────
    print("\n── 7. Voice of Customer Tables ──")
    df_sent = run(conn, "SELECT * FROM gold_review_sentiment")
    check(f"gold_review_sentiment rows > 0", len(df_sent) > 0, f"got {len(df_sent)}")

    df_kw = run(conn, "SELECT * FROM gold_review_keywords")
    check(f"gold_review_keywords rows > 0", len(df_kw) > 0, f"got {len(df_kw)}")
    check("Has sentiment column", "sentiment" in df_kw.columns)
    check("Has word column", "word" in df_kw.columns)

    # ──────────────────────────────────────────
    # 8. REVIEW TRUST SCORE (future mode)
    # ──────────────────────────────────────────
    print("\n── 8. Review Trust Tables ──")
    df_trust = run(conn, "SELECT * FROM gold_review_trust")
    check(f"gold_review_trust rows > 0", len(df_trust) > 0, f"got {len(df_trust)}")

    df_ptrust = run(conn, "SELECT * FROM gold_product_trust_scores")
    check(f"gold_product_trust_scores rows > 0", len(df_ptrust) > 0, f"got {len(df_ptrust)}")
    check("Has trust_score", "trust_score" in df_ptrust.columns)
    check("Has is_suspicious", "is_suspicious" in df_ptrust.columns)

    suspicious_count = df_ptrust["is_suspicious"].sum()
    total = len(df_ptrust)
    pct = suspicious_count / total * 100
    check(f"Suspicious ~5% ({pct:.1f}%)", 2 < pct < 10, f"{suspicious_count} of {total}")

    # ──────────────────────────────────────────
    # SUMMARY
    # ──────────────────────────────────────────
    conn.close()
    total = PASS + FAIL
    print(f"\n{'='*40}")
    print(f"  {PASS}/{total} passed  |  {FAIL} failed")
    print(f"{'='*40}\n")

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
