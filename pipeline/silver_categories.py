"""Silver layer: Category profiles from full 35M McAuley metadata."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

print("Creating silver_categories...")
con.sql("""
    CREATE OR REPLACE TABLE silver_categories AS
    SELECT
        main_category,
        COUNT(*) AS product_count,
        COUNT(DISTINCT store) AS store_count,
        COUNT(DISTINCT brand) AS brand_count,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(review_count), 1) AS avg_reviews,
        ROUND(AVG(price), 2) AS avg_price,
        ROUND(MEDIAN(price), 2) AS median_price,
        ROUND(SUM(has_features) * 100.0 / COUNT(*), 1) AS pct_with_features,
        ROUND(SUM(has_description) * 100.0 / COUNT(*), 1) AS pct_with_description,
        ROUND(SUM(has_brand) * 100.0 / COUNT(*), 1) AS pct_with_brand,
        ROUND(SUM(has_store) * 100.0 / COUNT(*), 1) AS pct_with_store
    FROM silver_products_full
    GROUP BY main_category
    ORDER BY product_count DESC
""")

result = con.sql("SELECT COUNT(*) FROM silver_categories").fetchone()
print(f"silver_categories: {result[0]} categories")

con.close()
