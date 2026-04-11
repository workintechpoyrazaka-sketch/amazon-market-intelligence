import duckdb
con = duckdb.connect('data/amazon_intelligence.duckdb')
print("Creating gold_temporal_trends...")
con.sql("""
    CREATE OR REPLACE TABLE gold_temporal_trends AS
    SELECT
        source_category,
        review_year,
        review_month,
        COUNT(*) AS review_count,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(MEDIAN(rating), 1) AS median_rating,
        ROUND(SUM(CASE WHEN verified_purchase THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_verified,
        ROUND(SUM(CASE WHEN image_count > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_with_images,
        ROUND(AVG(helpful_vote), 2) AS avg_helpful_votes,
        ROUND(AVG(CASE WHEN has_text THEN LENGTH(text) END), 1) AS avg_text_length,
        SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) AS negative_reviews,
        SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) AS neutral_reviews,
        SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) AS positive_reviews,
        ROUND(SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_negative
    FROM silver_reviews
    WHERE review_year >= 2000 AND review_year <= 2025
    GROUP BY source_category, review_year, review_month
    ORDER BY source_category, review_year, review_month
""")
result = con.sql("SELECT COUNT(*) FROM gold_temporal_trends").fetchone()[0]
print(f"gold_temporal_trends: {result} rows (category x year x month)")
print("\nReview volume trend (all categories, last 5 years):")
con.sql("""
    SELECT review_year, SUM(review_count) AS total_reviews, ROUND(AVG(avg_rating), 2) AS avg_rating
    FROM gold_temporal_trends
    WHERE review_year >= 2019
    GROUP BY review_year
    ORDER BY review_year
""").show()
con.close()
