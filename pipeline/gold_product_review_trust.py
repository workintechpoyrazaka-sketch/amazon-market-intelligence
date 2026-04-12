import duckdb, time
con = duckdb.connect('C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/amazon_intelligence.duckdb')
con.sql("SET temp_directory='C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/tmp'")
print("Creating gold_product_review_trust... (filtered to Kaggle products only)")
start = time.time()
con.sql("""
    CREATE OR REPLACE TABLE gold_product_review_trust AS
    SELECT
        r.parent_asin,
        r.source_category,
        COUNT(*) AS review_count,
        COUNT(DISTINCT r.user_id) AS unique_reviewers,
        ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT r.user_id), 2) AS reviews_per_reviewer,
        ROUND(SUM(CASE WHEN r.rating IN (1, 5) THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_extreme_ratings,
        ROUND(SUM(CASE WHEN r.rating = 5 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_5star,
        ROUND(SUM(CASE WHEN r.rating = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_1star,
        ROUND(SUM(CASE WHEN r.verified_purchase THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_verified,
        ROUND(SUM(CASE WHEN NOT r.verified_purchase AND r.rating = 5 THEN 1 ELSE 0 END) * 100.0 
            / NULLIF(SUM(CASE WHEN NOT r.verified_purchase THEN 1 ELSE 0 END), 0), 1) AS pct_5star_unverified,
        ROUND(SUM(CASE WHEN r.verified_purchase AND r.rating = 5 THEN 1 ELSE 0 END) * 100.0 
            / NULLIF(SUM(CASE WHEN r.verified_purchase THEN 1 ELSE 0 END), 0), 1) AS pct_5star_verified,
        ROUND(SUM(CASE WHEN r.has_text THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_with_text,
        ROUND(AVG(CASE WHEN r.has_text THEN r.text_length END), 1) AS avg_text_length,
        ROUND(SUM(CASE WHEN r.has_text AND r.text_length < 20 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_very_short_text,
        ROUND(COUNT(*) * 1.0 / GREATEST(DATEDIFF('day', MIN(r.review_date), MAX(r.review_date)), 1), 4) AS reviews_per_day,
        ROUND(SUM(CASE WHEN r.helpful_vote > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_with_helpful_votes
    FROM silver_reviews r
    WHERE r.parent_asin IN (SELECT DISTINCT asin FROM silver_products)
    GROUP BY r.parent_asin, r.source_category
""")
elapsed = time.time() - start
result = con.sql("SELECT COUNT(*) FROM gold_product_review_trust").fetchone()[0]
print(f"gold_product_review_trust: {result:,} rows in {elapsed/60:.1f} min")
print("\nMost suspicious (high extreme ratings + low verified):")
con.sql("""
    SELECT parent_asin, review_count, pct_extreme_ratings, pct_verified, pct_very_short_text, reviews_per_day
    FROM gold_product_review_trust
    WHERE review_count >= 50
    ORDER BY pct_extreme_ratings DESC, pct_verified ASC
    LIMIT 5
""").show()
con.close()
