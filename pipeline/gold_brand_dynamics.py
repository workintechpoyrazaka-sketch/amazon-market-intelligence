"""Gold layer: Brand dynamics for Competitive Positioning mode."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

print("Creating gold_brand_dynamics...")
con.sql("""
    CREATE OR REPLACE TABLE gold_brand_dynamics AS
    SELECT
        subcategory,
        CASE WHEN has_brand = 1 THEN 'Branded' ELSE 'Unbranded' END AS brand_status,
        COUNT(*) AS product_count,
        ROUND(AVG(price), 2) AS avg_price,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(review_count), 1) AS avg_reviews,
        SUM(bought_last_month) AS total_units_sold,
        ROUND(SUM(estimated_revenue), 2) AS total_revenue,
        ROUND(AVG(estimated_revenue), 2) AS avg_revenue_per_product,
        ROUND(SUM(CASE WHEN bought_last_month > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_active,
        ROUND(SUM(CASE WHEN is_best_seller THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_best_sellers,
        ROUND(AVG(discount_pct), 1) AS avg_discount_pct
    FROM silver_products
    GROUP BY subcategory, brand_status
    ORDER BY subcategory, total_revenue DESC
""")

result = con.sql("SELECT COUNT(*) FROM gold_brand_dynamics").fetchone()[0]
print(f"gold_brand_dynamics: {result} rows (subcategory x brand_status)")

print("\nBiggest brand advantage (by revenue per product):")
advantage = con.sql("""
    WITH pivoted AS (
        SELECT 
            subcategory,
            MAX(CASE WHEN brand_status = 'Branded' THEN avg_revenue_per_product END) AS branded_rev,
            MAX(CASE WHEN brand_status = 'Unbranded' THEN avg_revenue_per_product END) AS unbranded_rev
        FROM gold_brand_dynamics
        GROUP BY subcategory
    )
    SELECT subcategory, 
           branded_rev, 
           unbranded_rev,
           ROUND(branded_rev / NULLIF(unbranded_rev, 0), 1) AS brand_multiplier
    FROM pivoted
    WHERE branded_rev IS NOT NULL AND unbranded_rev IS NOT NULL AND unbranded_rev > 0
    ORDER BY brand_multiplier DESC
    LIMIT 10
""").fetchall()
for r in advantage:
    print(f"  {r[0]}: Branded ${r[1]:,.0f} vs Unbranded ${r[2]:,.0f} ({r[3]}x)")

con.close()
