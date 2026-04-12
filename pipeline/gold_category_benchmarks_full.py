import duckdb, time
con = duckdb.connect('C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/amazon_intelligence.duckdb')
print("Creating gold_category_benchmarks_full...")
start = time.time()
con.sql("""
    CREATE OR REPLACE TABLE gold_category_benchmarks_full AS
    SELECT
        sp.subcategory,
        COUNT(*) AS product_count,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sp.price), 2) AS price_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY sp.price), 2) AS price_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sp.price), 2) AS price_p75,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sp.rating), 2) AS rating_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY sp.rating), 2) AS rating_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sp.rating), 2) AS rating_p75,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sp.review_count), 0) AS reviews_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY sp.review_count), 0) AS reviews_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sp.review_count), 0) AS reviews_p75,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sp.bought_last_month), 0) AS sales_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY sp.bought_last_month), 0) AS sales_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sp.bought_last_month), 0) AS sales_p75,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sp.estimated_revenue), 2) AS revenue_p25,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY sp.estimated_revenue), 2) AS revenue_p50,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sp.estimated_revenue), 2) AS revenue_p75,
        ROUND(AVG(sp.title_length), 1) AS avg_title_length,
        ROUND(SUM(sp.has_features) * 100.0 / COUNT(*), 1) AS pct_with_features,
        ROUND(SUM(sp.has_description) * 100.0 / COUNT(*), 1) AS pct_with_description,
        ROUND(SUM(sp.has_brand) * 100.0 / COUNT(*), 1) AS pct_with_brand,
        ROUND(AVG(sp.discount_pct), 1) AS avg_discount_pct,
        ROUND(AVG(r.avg_rating), 2) AS avg_review_rating,
        ROUND(AVG(r.pct_verified), 1) AS avg_pct_verified,
        ROUND(AVG(r.pct_negative), 1) AS avg_pct_negative,
        ROUND(AVG(r.reviews_per_month), 2) AS avg_reviews_per_month,
        ROUND(AVG(r.avg_text_length), 1) AS avg_review_text_length,
        COUNT(r.parent_asin) AS products_with_reviews
    FROM silver_products sp
    LEFT JOIN gold_product_review_summary r ON sp.asin = r.parent_asin
    GROUP BY sp.subcategory
    ORDER BY product_count DESC
""")
elapsed = time.time() - start
result = con.sql("SELECT COUNT(*) FROM gold_category_benchmarks_full").fetchone()[0]
print(f"gold_category_benchmarks_full: {result} rows in {elapsed:.1f}s")
print("\nSample - review match rate:")
con.sql("""
    SELECT subcategory, product_count, products_with_reviews,
        ROUND(products_with_reviews * 100.0 / product_count, 1) AS pct_matched
    FROM gold_category_benchmarks_full
    ORDER BY product_count DESC
    LIMIT 5
""").show()
con.close()
