"""Gold layer: Product benchmarks for Health Check mode."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

print("Creating gold_product_benchmarks...")
con.sql("""
    CREATE OR REPLACE TABLE gold_product_benchmarks AS
    SELECT
        subcategory,
        COUNT(*) AS product_count,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price), 2) AS price_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price), 2) AS price_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price), 2) AS price_p75,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY review_count), 0) AS reviews_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY review_count), 0) AS reviews_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY review_count), 0) AS reviews_p75,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY rating), 2) AS rating_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY rating), 2) AS rating_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY rating), 2) AS rating_p75,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY bought_last_month), 0) AS sales_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY bought_last_month), 0) AS sales_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY bought_last_month), 0) AS sales_p75,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY estimated_revenue), 2) AS revenue_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY estimated_revenue), 2) AS revenue_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY estimated_revenue), 2) AS revenue_p75
    FROM silver_products
    WHERE price IS NOT NULL
    GROUP BY subcategory
    ORDER BY product_count DESC
""")

result = con.sql("SELECT COUNT(*) FROM gold_product_benchmarks").fetchone()[0]
print(f"gold_product_benchmarks: {result} subcategories")

print("\nSample - Kitchen and Dining benchmarks:")
sample = con.sql("""
    SELECT price_p25, price_p50, price_p75, reviews_p25, reviews_p50, reviews_p75, sales_p50
    FROM gold_product_benchmarks
    WHERE subcategory = 'Kitchen & Dining'
""").fetchone()
print(f"  Price: ${sample[0]} / ${sample[1]} / ${sample[2]} (p25/p50/p75)")
print(f"  Reviews: {sample[3]} / {sample[4]} / {sample[5]} (p25/p50/p75)")
print(f"  Median monthly sales: {sample[6]}")

con.close()
