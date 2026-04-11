import duckdb
con = duckdb.connect('data/amazon_intelligence.duckdb')
print("Creating gold_bestseller_analysis...")
con.sql("""
    CREATE OR REPLACE TABLE gold_bestseller_analysis AS
    SELECT
        subcategory,
        COUNT(*) AS total_products,
        SUM(CAST(is_best_seller AS INT)) AS bestseller_count,
        ROUND(SUM(CAST(is_best_seller AS INT)) * 100.0 / COUNT(*), 2) AS pct_bestsellers,
        -- Bestseller vs non-bestseller performance
        ROUND(AVG(CASE WHEN is_best_seller THEN price END), 2) AS avg_price_bestseller,
        ROUND(AVG(CASE WHEN NOT is_best_seller THEN price END), 2) AS avg_price_non_bestseller,
        ROUND(AVG(CASE WHEN is_best_seller THEN rating END), 2) AS avg_rating_bestseller,
        ROUND(AVG(CASE WHEN NOT is_best_seller THEN rating END), 2) AS avg_rating_non_bestseller,
        ROUND(AVG(CASE WHEN is_best_seller THEN review_count END), 1) AS avg_reviews_bestseller,
        ROUND(AVG(CASE WHEN NOT is_best_seller THEN review_count END), 1) AS avg_reviews_non_bestseller,
        ROUND(AVG(CASE WHEN is_best_seller THEN estimated_revenue END), 2) AS avg_rev_bestseller,
        ROUND(AVG(CASE WHEN NOT is_best_seller THEN estimated_revenue END), 2) AS avg_rev_non_bestseller,
        ROUND(AVG(CASE WHEN is_best_seller THEN bought_last_month END), 1) AS avg_sales_bestseller,
        ROUND(AVG(CASE WHEN NOT is_best_seller THEN bought_last_month END), 1) AS avg_sales_non_bestseller,
        -- Revenue share
        ROUND(SUM(CASE WHEN is_best_seller THEN estimated_revenue ELSE 0 END) * 100.0 
            / NULLIF(SUM(estimated_revenue), 0), 1) AS pct_revenue_from_bestsellers,
        -- Bestseller badge multiplier
        ROUND(AVG(CASE WHEN is_best_seller THEN estimated_revenue END) 
            / NULLIF(AVG(CASE WHEN NOT is_best_seller THEN estimated_revenue END), 0), 1) AS bestseller_revenue_multiplier
    FROM silver_products
    GROUP BY subcategory
    ORDER BY bestseller_count DESC
""")
result = con.sql("SELECT COUNT(*) FROM gold_bestseller_analysis").fetchone()[0]
print(f"gold_bestseller_analysis: {result} rows")
print("\nTop 5 by bestseller multiplier:")
con.sql("""
    SELECT subcategory, bestseller_count, pct_bestsellers, 
        avg_rev_bestseller, avg_rev_non_bestseller, bestseller_revenue_multiplier
    FROM gold_bestseller_analysis
    WHERE bestseller_count >= 10
    ORDER BY bestseller_revenue_multiplier DESC
    LIMIT 5
""").show()
con.close()
