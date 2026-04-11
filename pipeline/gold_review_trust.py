import duckdb
con = duckdb.connect('data/amazon_intelligence.duckdb')
print("Creating gold_review_trust...")
con.sql("""
    CREATE OR REPLACE TABLE gold_review_trust AS
    SELECT
        source_category,
        COUNT(*) AS total_reviews,
        COUNT(DISTINCT user_id) AS unique_reviewers,
        ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_id), 2) AS reviews_per_reviewer,
        ROUND(SUM(CASE WHEN verified_purchase THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_verified,
        ROUND(SUM(CASE WHEN NOT verified_purchase THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_unverified,
        ROUND(SUM(CASE WHEN image_count > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_with_images,
        ROUND(SUM(CASE WHEN has_text THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_with_text,
        ROUND(AVG(helpful_vote), 2) AS avg_helpful_votes,
        ROUND(AVG(CASE WHEN has_text THEN LENGTH(text) END), 1) AS avg_text_length,
        -- Rating distribution
        ROUND(SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_5star,
        ROUND(SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_4star,
        ROUND(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_3star,
        ROUND(SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_2star,
        ROUND(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_1star,
        -- Trust signals
        ROUND(SUM(CASE WHEN rating IN (1, 5) THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_extreme_ratings,
        ROUND(SUM(CASE WHEN NOT verified_purchase AND rating = 5 THEN 1 ELSE 0 END) * 100.0 
            / NULLIF(SUM(CASE WHEN NOT verified_purchase THEN 1 ELSE 0 END), 0), 1) AS pct_5star_among_unverified,
        ROUND(SUM(CASE WHEN verified_purchase AND rating = 5 THEN 1 ELSE 0 END) * 100.0 
            / NULLIF(SUM(CASE WHEN verified_purchase THEN 1 ELSE 0 END), 0), 1) AS pct_5star_among_verified
    FROM silver_reviews
    GROUP BY source_category
    ORDER BY total_reviews DESC
""")
result = con.sql("SELECT COUNT(*) FROM gold_review_trust").fetchone()[0]
print(f"gold_review_trust: {result} rows (one per category)")
print("\nTrust signals - top suspicious (highest unverified 5-star gap):")
con.sql("""
    SELECT source_category, pct_verified, pct_5star_among_unverified, pct_5star_among_verified,
        ROUND(pct_5star_among_unverified - pct_5star_among_verified, 1) AS unverified_5star_gap
    FROM gold_review_trust
    ORDER BY unverified_5star_gap DESC
    LIMIT 5
""").show()
con.close()
