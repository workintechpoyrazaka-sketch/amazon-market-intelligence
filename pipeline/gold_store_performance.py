"""Gold layer: Store performance for Health Check mode."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

print("Creating gold_store_performance...")
con.sql("""
    CREATE OR REPLACE TABLE gold_store_performance AS
    SELECT
        s.store,
        s.store_type,
        s.product_count AS ecosystem_products,
        s.category_count,
        s.brand_count,
        s.avg_rating AS ecosystem_avg_rating,
        s.avg_reviews AS ecosystem_avg_reviews,
        COUNT(sp.asin) AS kaggle_products,
        ROUND(AVG(sp.price), 2) AS avg_price,
        ROUND(SUM(sp.estimated_revenue), 2) AS total_revenue,
        ROUND(AVG(sp.estimated_revenue), 2) AS avg_revenue_per_product,
        SUM(sp.bought_last_month) AS total_units_sold,
        ROUND(SUM(CASE WHEN sp.bought_last_month > 0 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(sp.asin), 0), 1) AS pct_active,
        ROUND(AVG(sp.rating), 2) AS avg_rating,
        ROUND(AVG(sp.review_count), 1) AS avg_reviews
    FROM silver_stores s
    LEFT JOIN silver_products sp ON s.store = sp.store
    GROUP BY s.store, s.store_type, s.product_count, s.category_count, s.brand_count, s.avg_rating, s.avg_reviews
    HAVING COUNT(sp.asin) > 0
""")

result = con.sql("SELECT COUNT(*) FROM gold_store_performance").fetchone()[0]
print(f"gold_store_performance: {result} stores with sales data")

print("\nPerformance by store type:")
by_type = con.sql("""
    SELECT store_type, COUNT(*) AS stores, 
           ROUND(AVG(avg_revenue_per_product), 2) AS avg_rev_per_product,
           ROUND(AVG(pct_active), 1) AS avg_pct_active
    FROM gold_store_performance
    GROUP BY store_type
    ORDER BY avg_rev_per_product DESC
""").fetchall()
for r in by_type:
    print(f"  {r[0]}: {r[1]} stores, ${r[2]:,.0f}/product, {r[3]}% active")

con.close()
