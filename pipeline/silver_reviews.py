import duckdb
con = duckdb.connect('data/amazon_intelligence.duckdb')
print("Creating silver_reviews VIEW...")
con.sql("""
    CREATE OR REPLACE VIEW silver_reviews AS
    SELECT
        rating,
        title,
        text,
        asin,
        parent_asin,
        user_id,
        timestamp,
        CAST(to_timestamp(timestamp / 1000) AS DATE) AS review_date,
        YEAR(CAST(to_timestamp(timestamp / 1000) AS DATE)) AS review_year,
        MONTH(CAST(to_timestamp(timestamp / 1000) AS DATE)) AS review_month,
        helpful_vote,
        verified_purchase,
        image_count,
        source_category,
        LENGTH(text) AS text_length,
        has_text,
        has_title,
        has_helpful_votes
    FROM bronze_reviews
""")
result = con.sql("SELECT COUNT(*) FROM silver_reviews LIMIT 1").fetchone()[0]
print(f"silver_reviews VIEW created ({result:,} rows)")
sample = con.sql("SELECT review_date, review_year, review_month, rating, verified_purchase FROM silver_reviews LIMIT 5")
sample.show()
con.close()
