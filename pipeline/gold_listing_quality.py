import duckdb
con = duckdb.connect('data/amazon_intelligence.duckdb')
print("Creating gold_listing_quality...")
con.sql("""
    CREATE OR REPLACE TABLE gold_listing_quality AS
    SELECT
        subcategory,
        COUNT(*) AS product_count,
        ROUND(AVG(title_length), 1) AS avg_title_length,
        ROUND(MEDIAN(title_length), 1) AS median_title_length,
        ROUND(SUM(has_features) * 100.0 / COUNT(*), 1) AS pct_with_features,
        ROUND(SUM(has_description) * 100.0 / COUNT(*), 1) AS pct_with_description,
        ROUND(SUM(has_brand) * 100.0 / COUNT(*), 1) AS pct_with_brand,
        ROUND(SUM(has_store) * 100.0 / COUNT(*), 1) AS pct_with_store,
        -- Performance by listing completeness
        ROUND(AVG(CASE WHEN has_features = 1 THEN estimated_revenue END), 2) AS avg_rev_with_features,
        ROUND(AVG(CASE WHEN has_features = 0 THEN estimated_revenue END), 2) AS avg_rev_without_features,
        ROUND(AVG(CASE WHEN has_description = 1 THEN estimated_revenue END), 2) AS avg_rev_with_description,
        ROUND(AVG(CASE WHEN has_description = 0 THEN estimated_revenue END), 2) AS avg_rev_without_description,
        ROUND(AVG(CASE WHEN has_brand = 1 THEN estimated_revenue END), 2) AS avg_rev_with_brand,
        ROUND(AVG(CASE WHEN has_brand = 0 THEN estimated_revenue END), 2) AS avg_rev_without_brand,
        -- Title length vs performance
        ROUND(AVG(CASE WHEN title_length < 50 THEN estimated_revenue END), 2) AS avg_rev_short_title,
        ROUND(AVG(CASE WHEN title_length BETWEEN 50 AND 100 THEN estimated_revenue END), 2) AS avg_rev_medium_title,
        ROUND(AVG(CASE WHEN title_length BETWEEN 100 AND 150 THEN estimated_revenue END), 2) AS avg_rev_long_title,
        ROUND(AVG(CASE WHEN title_length > 150 THEN estimated_revenue END), 2) AS avg_rev_very_long_title,
        -- Listing completeness score (0-4)
        ROUND(AVG(has_features + has_description + has_brand + has_store), 2) AS avg_completeness_score,
        ROUND(AVG(CASE WHEN (has_features + has_description + has_brand + has_store) >= 3 THEN estimated_revenue END), 2) AS avg_rev_high_completeness,
        ROUND(AVG(CASE WHEN (has_features + has_description + has_brand + has_store) <= 1 THEN estimated_revenue END), 2) AS avg_rev_low_completeness
    FROM silver_products
    GROUP BY subcategory
    ORDER BY product_count DESC
""")
result = con.sql("SELECT COUNT(*) FROM gold_listing_quality").fetchone()[0]
print(f"gold_listing_quality: {result} rows")
print("\nTop 5 by completeness impact:")
con.sql("""
    SELECT subcategory, avg_completeness_score, avg_rev_high_completeness, avg_rev_low_completeness,
        ROUND(avg_rev_high_completeness / NULLIF(avg_rev_low_completeness, 0), 1) AS completeness_multiplier
    FROM gold_listing_quality
    WHERE avg_rev_high_completeness IS NOT NULL AND avg_rev_low_completeness > 0
    ORDER BY completeness_multiplier DESC
    LIMIT 5
""").show()
con.close()
