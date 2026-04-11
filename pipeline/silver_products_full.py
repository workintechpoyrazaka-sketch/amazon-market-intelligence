"""Silver layer: Full McAuley metadata (35M) — VIEW, no data copy."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

con.sql("""
    CREATE OR REPLACE VIEW silver_products_full AS
    SELECT
        parent_asin,
        main_category,
        title,
        average_rating AS rating,
        rating_number AS review_count,
        CASE 
            WHEN price = '—' OR price IS NULL THEN NULL
            ELSE TRY_CAST(REPLACE(REPLACE(price, '$', ''), ',', '') AS DOUBLE)
        END AS price,
        store,
        details_brand AS brand,
        details_manufacturer AS manufacturer,
        features,
        description,
        categories,
        LENGTH(title) AS title_length,
        CASE WHEN store IS NOT NULL THEN 1 ELSE 0 END AS has_store,
        CASE WHEN details_brand IS NOT NULL THEN 1 ELSE 0 END AS has_brand,
        CASE WHEN features IS NOT NULL AND TRIM(features) != '' AND TRIM(features) != '[]' THEN 1 ELSE 0 END AS has_features,
        CASE WHEN description IS NOT NULL AND TRIM(description) != '' AND TRIM(description) != '[]' THEN 1 ELSE 0 END AS has_description,
        flag_no_price,
        flag_no_store,
        flag_no_brand,
        flag_no_title,
        flag_no_ratings
    FROM bronze_mcauley_metadata
    WHERE main_category IS NOT NULL
""")

print("silver_products_full VIEW created.")
con.close()
