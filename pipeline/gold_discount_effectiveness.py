import duckdb
con = duckdb.connect('data/amazon_intelligence.duckdb')
print("Creating gold_discount_effectiveness...")
con.sql("""
    CREATE OR REPLACE TABLE gold_discount_effectiveness AS
    SELECT
        subcategory,
        CASE
            WHEN discount_pct IS NULL OR discount_pct <= 0 THEN 'No Discount'
            WHEN discount_pct < 20 THEN 'Light (1-19%)'
            WHEN discount_pct < 50 THEN 'Medium (20-49%)'
            ELSE 'Deep (50%+)'
        END AS discount_tier,
        COUNT(*) AS product_count,
        ROUND(AVG(discount_pct), 1) AS avg_discount,
        ROUND(AVG(price), 2) AS avg_price,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(review_count), 1) AS avg_reviews,
        SUM(bought_last_month) AS total_units_sold,
        ROUND(SUM(estimated_revenue), 2) AS total_revenue,
        ROUND(AVG(estimated_revenue), 2) AS avg_revenue_per_product,
        ROUND(SUM(CASE WHEN bought_last_month > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_active,
        ROUND(SUM(CASE WHEN is_best_seller THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_best_sellers
    FROM silver_products
    WHERE listPrice IS NOT NULL AND listPrice > 0
    GROUP BY subcategory, discount_tier
    ORDER BY subcategory, total_revenue DESC
""")
result = con.sql("SELECT COUNT(*) FROM gold_discount_effectiveness").fetchone()[0]
print(f"gold_discount_effectiveness: {result} rows (subcategory x discount_tier)")
print("\nSample - Kitchen and Dining:")
con.sql("""
    SELECT discount_tier, product_count, total_revenue, avg_revenue_per_product, pct_active
    FROM gold_discount_effectiveness
    WHERE subcategory = 'Kitchen & Dining'
    ORDER BY total_revenue DESC
""").show()
con.close()
