"""Gold layer: Category landscape for Category Scout mode.
Two granularities: subcategory (full 1.4M revenue) + main_category (35M ecosystem)."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

print("Creating gold_subcategory_landscape...")
con.sql("""
    CREATE OR REPLACE TABLE gold_subcategory_landscape AS
    SELECT
        subcategory,
        COUNT(*) AS product_count,
        ROUND(AVG(price), 2) AS avg_price,
        ROUND(MEDIAN(price), 2) AS median_price,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(review_count), 1) AS avg_reviews,
        SUM(bought_last_month) AS total_units_sold,
        ROUND(SUM(estimated_revenue), 2) AS total_revenue,
        ROUND(AVG(estimated_revenue), 2) AS avg_revenue_per_product,
        ROUND(SUM(CASE WHEN is_best_seller THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_best_sellers,
        ROUND(SUM(CASE WHEN bought_last_month > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_active,
        ROUND(SUM(CASE WHEN review_count = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_zero_reviews,
        ROUND(AVG(discount_pct), 1) AS avg_discount_pct,
        ROUND(SUM(has_brand) * 100.0 / COUNT(*), 1) AS pct_with_brand,
        ROUND(SUM(has_features) * 100.0 / COUNT(*), 1) AS pct_with_features,
        ROUND(SUM(has_description) * 100.0 / COUNT(*), 1) AS pct_with_description,
        ROUND(SUM(has_store) * 100.0 / COUNT(*), 1) AS pct_with_store
    FROM silver_products
    GROUP BY subcategory
    ORDER BY total_revenue DESC
""")

sub_count = con.sql("SELECT COUNT(*) FROM gold_subcategory_landscape").fetchone()[0]
print(f"gold_subcategory_landscape: {sub_count} subcategories (full 1.4M revenue)")

print("\nCreating gold_main_category_landscape...")
con.sql("""
    CREATE OR REPLACE TABLE gold_main_category_landscape AS
    WITH kaggle_revenue AS (
        SELECT
            main_category,
            COUNT(*) AS kaggle_products,
            SUM(bought_last_month) AS total_units_sold,
            ROUND(SUM(estimated_revenue), 2) AS total_revenue,
            ROUND(AVG(estimated_revenue), 2) AS avg_revenue_per_product,
            ROUND(AVG(price), 2) AS avg_price,
            ROUND(AVG(rating), 2) AS avg_rating,
            ROUND(SUM(CASE WHEN bought_last_month > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_active
        FROM silver_products
        WHERE main_category IS NOT NULL
        GROUP BY main_category
    )
    SELECT
        e.main_category,
        e.product_count AS ecosystem_products,
        e.store_count,
        e.brand_count,
        k.kaggle_products,
        ROUND(k.kaggle_products * 100.0 / e.product_count, 2) AS kaggle_coverage_pct,
        k.total_units_sold,
        k.total_revenue,
        k.avg_revenue_per_product,
        k.avg_price,
        k.avg_rating,
        k.pct_active,
        ROUND(e.product_count * 1.0 / e.store_count, 1) AS products_per_store,
        ROUND(k.total_revenue / NULLIF(e.store_count, 0), 2) AS revenue_per_store,
        e.pct_with_features,
        e.pct_with_description,
        e.pct_with_brand,
        e.pct_with_store
    FROM silver_categories e
    LEFT JOIN kaggle_revenue k ON e.main_category = k.main_category
    ORDER BY k.total_revenue DESC NULLS LAST
""")

main_count = con.sql("SELECT COUNT(*) FROM gold_main_category_landscape").fetchone()[0]
print(f"gold_main_category_landscape: {main_count} main categories (35M ecosystem)")

print("\nTop 5 subcategories by revenue:")
top_sub = con.sql("SELECT subcategory, total_revenue, pct_active FROM gold_subcategory_landscape LIMIT 5").fetchall()
for r in top_sub:
    print(f"  {r[0]}: ${r[1]:,.0f} revenue, {r[2]}% active")

print("\nTop 5 main categories by revenue:")
top_main = con.sql("SELECT main_category, total_revenue, ecosystem_products FROM gold_main_category_landscape WHERE total_revenue IS NOT NULL LIMIT 5").fetchall()
for r in top_main:
    print(f"  {r[0]}: ${r[1]:,.0f} revenue, {r[2]:,} ecosystem products")

con.close()
