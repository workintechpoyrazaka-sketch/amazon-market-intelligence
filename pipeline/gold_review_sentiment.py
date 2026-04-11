import duckdb
con = duckdb.connect('data/amazon_intelligence.duckdb')
print("Creating gold_review_sentiment...")
con.sql("""
    CREATE OR REPLACE TABLE gold_review_sentiment AS
    SELECT
        source_category,
        COUNT(*) AS total_reviews,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(MEDIAN(rating), 1) AS median_rating,
        -- Sentiment proxy from ratings
        SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) AS positive_count,
        SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) AS neutral_count,
        SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) AS negative_count,
        ROUND(SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_positive,
        ROUND(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_neutral,
        ROUND(SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_negative,
        -- Text engagement
        ROUND(SUM(CASE WHEN has_text THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_with_text,
        ROUND(AVG(CASE WHEN has_text THEN LENGTH(text) END), 1) AS avg_text_length,
        ROUND(AVG(CASE WHEN rating <= 2 AND has_text THEN LENGTH(text) END), 1) AS avg_text_length_negative,
        ROUND(AVG(CASE WHEN rating >= 4 AND has_text THEN LENGTH(text) END), 1) AS avg_text_length_positive,
        -- Negative reviews tend to be longer = more detailed complaints
        ROUND(AVG(CASE WHEN rating <= 2 AND has_text THEN LENGTH(text) END) 
            / NULLIF(AVG(CASE WHEN rating >= 4 AND has_text THEN LENGTH(text) END), 0), 2) AS negative_verbosity_ratio,
        -- Helpful vote patterns by sentiment
        ROUND(AVG(CASE WHEN rating <= 2 THEN helpful_vote END), 2) AS avg_helpful_negative,
        ROUND(AVG(CASE WHEN rating >= 4 THEN helpful_vote END), 2) AS avg_helpful_positive,
        -- Image attachment by sentiment
        ROUND(SUM(CASE WHEN rating <= 2 AND image_count > 0 THEN 1 ELSE 0 END) * 100.0 
            / NULLIF(SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END), 0), 1) AS pct_images_negative,
        ROUND(SUM(CASE WHEN rating >= 4 AND image_count > 0 THEN 1 ELSE 0 END) * 100.0 
            / NULLIF(SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END), 0), 1) AS pct_images_positive
    FROM silver_reviews
    GROUP BY source_category
    ORDER BY total_reviews DESC
""")
result = con.sql("SELECT COUNT(*) FROM gold_review_sentiment").fetchone()[0]
print(f"gold_review_sentiment: {result} rows")
print("\nMost negative categories:")
con.sql("""
    SELECT source_category, pct_negative, avg_text_length_negative, negative_verbosity_ratio, avg_helpful_negative
    FROM gold_review_sentiment
    ORDER BY pct_negative DESC
    LIMIT 5
""").show()
con.close()
