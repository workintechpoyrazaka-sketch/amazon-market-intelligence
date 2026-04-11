"""Gold layer: Price positioning analysis for Competitive Positioning mode."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

print("Creating gold_price_positioning...")
con.sql("""
    CREATE OR REPLACE TABLE gold_price_positioning AS
    SELECT
        subcategory,
        price_tier,
        COUNT(*) AS product_count,
        ROUND(AVG(price), 2) AS avg_price,
        ROUND(MEDIAN(price), 2) AS median_price,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(review_count), 1) AS avg_reviews,
        SUM(bought_last_month) AS total_units_sold,
        ROUND(SUM(estimated_revenue), 2) AS total_revenue,
        ROUND(AVG(estimated_revenue), 2) AS avg_revenue_per_product,
        ROUND(SUM(CASE WHEN bought_last_month > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_active,
        ROUND(SUM(CASE WHEN is_best_seller THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_best_sellers,
        ROUND(AVG(discount_pct), 1) AS avg_discount_pct,
        ROUND(SUM(has_brand) * 100.0 / COUNT(*), 1) AS pct_branded,
        ROUND(AVG(title_length), 1) AS avg_title_length,
        ROUND(SUM(has_features) * 100.0 / COUNT(*), 1) AS pct_with_features
    FROM silver_products
    GROUP BY subcategory, price_tier
    ORDER BY subcategory, total_revenue DESC
""")

result = con.sql("SELECT COUNT(*) FROM gold_price_positioning").fetchone()[0]
print(f"gold_price_positioning: {result} rows (subcategory x price_tier)")

print("\nSample - Kitchen and Dining by price tier:")
sample = con.sql("""
    SELECT price_tier, product_count, total_revenue, avg_revenue_per_product, pct_active
    FROM gold_price_positioning
    WHERE subcategory = 'Kitchen & Dining'
    ORDER BY total_revenue DESC
""").fetchall()
for r in sample:
    print(f"  {r[0]}: {r[1]} products, ${r[2]:,.0f} revenue, ${r[3]:,.0f}/product, {r[4]}% active")

con.close()
