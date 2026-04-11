import duckdb, time

con = duckdb.connect('C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/amazon_intelligence.duckdb')

start = time.time()
con.sql("""
    CREATE OR REPLACE TABLE bronze_reviews_test AS
    SELECT 
        rating, title, text, asin, parent_asin, user_id,
        timestamp, helpful_vote, verified_purchase,
        len(images) AS image_count,
        'All_Beauty' AS source_category
    FROM read_json_auto(
        'C:/Users/thinkpad/Desktop/amazon-market-intelligence/collection/mcauley_reviews/All_Beauty.jsonl',
        maximum_object_size=10485760
    )
""")
elapsed = time.time() - start

count = con.sql("SELECT COUNT(*) FROM bronze_reviews_test").fetchone()[0]
print(f"Rows: {count:,}")
print(f"Time: {elapsed:.1f} seconds")
print(f"Rate: {count/elapsed:,.0f} rows/sec")

con.sql("DROP TABLE bronze_reviews_test")
con.close()
