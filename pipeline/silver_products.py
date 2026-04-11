"""Silver layer: Enriched products (Kaggle + McAuley match)."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

con.sql("""
    CREATE OR REPLACE TABLE silver_products AS
    SELECT
        k.asin,
        c.category_name AS subcategory,
        m.main_category,
        k.title,
        k.price,
        k.listPrice,
        CASE 
            WHEN k.price > 0 AND k.listPrice > k.price 
            THEN ROUND((k.listPrice - k.price) / k.listPrice * 100, 1)
            ELSE NULL 
        END AS discount_pct,
        k.stars AS rating,
        k.reviews AS review_count,
        k.isBestSeller AS is_best_seller,
        k.boughtInLastMonth AS bought_last_month,
        ROUND(k.price * k.boughtInLastMonth, 2) AS estimated_revenue,
        CASE
            WHEN k.price IS NULL THEN 'Unknown'
            WHEN k.price < 10 THEN 'Budget'
            WHEN k.price < 25 THEN 'Low'
            WHEN k.price < 50 THEN 'Mid'
            WHEN k.price < 100 THEN 'Premium'
            ELSE 'Luxury'
        END AS price_tier,
        m.store,
        m.details_brand AS brand,
        m.details_manufacturer AS manufacturer,
        m.features,
        m.description,
        m.categories AS mcauley_categories,
        LENGTH(k.title) AS title_length,
        CASE WHEN m.features IS NOT NULL AND TRIM(m.features) != '' AND TRIM(m.features) != '[]' THEN 1 ELSE 0 END AS has_features,
        CASE WHEN m.description IS NOT NULL AND TRIM(m.description) != '' AND TRIM(m.description) != '[]' THEN 1 ELSE 0 END AS has_description,
        CASE WHEN m.store IS NOT NULL THEN 1 ELSE 0 END AS has_store,
        CASE WHEN m.details_brand IS NOT NULL THEN 1 ELSE 0 END AS has_brand,
        CASE WHEN m.parent_asin IS NOT NULL THEN 1 ELSE 0 END AS is_mcauley_matched,
        k.flag_no_price,
        k.flag_no_reviews,
        k.flag_no_sales,
        k.flag_no_rating,
        k.flag_no_title
    FROM bronze_kaggle_products k
    LEFT JOIN bronze_kaggle_categories c ON k.category_id = c.id
    LEFT JOIN bronze_mcauley_metadata m ON k.asin = m.parent_asin
""")

result = con.sql("SELECT COUNT(*) AS total, SUM(is_mcauley_matched) AS enriched FROM silver_products").fetchone()
print(f"silver_products: {result[0]} rows, {result[1]} enriched ({round(result[1]/result[0]*100,1)}%)")

con.close()
