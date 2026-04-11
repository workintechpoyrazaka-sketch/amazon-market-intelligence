"""Silver layer: Store profiles from full 35M McAuley metadata."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

print("Creating silver_stores...")
con.sql("""
    CREATE OR REPLACE TABLE silver_stores AS
    SELECT
        store,
        COUNT(*) AS product_count,
        COUNT(DISTINCT main_category) AS category_count,
        COUNT(DISTINCT brand) AS brand_count,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(review_count), 1) AS avg_reviews,
        SUM(has_features) AS products_with_features,
        SUM(has_description) AS products_with_description,
        CASE
            WHEN COUNT(DISTINCT main_category) = 1 THEN 'Specialist'
            WHEN COUNT(DISTINCT main_category) <= 3 THEN 'Focused'
            ELSE 'Generalist'
        END AS store_type
    FROM silver_products_full
    WHERE store IS NOT NULL
    GROUP BY store
""")

result = con.sql("""
    SELECT COUNT(*) AS total,
           COUNT(CASE WHEN store_type = 'Specialist' THEN 1 END) AS specialists,
           COUNT(CASE WHEN store_type = 'Focused' THEN 1 END) AS focused,
           COUNT(CASE WHEN store_type = 'Generalist' THEN 1 END) AS generalists
    FROM silver_stores
""").fetchone()
print(f"silver_stores: {result[0]} stores")
print(f"  Specialist: {result[1]}, Focused: {result[2]}, Generalist: {result[3]}")

con.close()
