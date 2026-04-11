import duckdb, time

con = duckdb.connect('C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/amazon_intelligence.duckdb')

# 1. Load Video_Games
print("Loading Video_Games...", flush=True)
start = time.time()
con.sql("""
    INSERT INTO bronze_reviews
    SELECT 
        rating, title, text, asin, parent_asin, user_id,
        timestamp, helpful_vote, verified_purchase,
        len(images) AS image_count,
        'Video_Games' AS source_category,
        (text IS NOT NULL AND text != '') AS has_text,
        (title IS NOT NULL AND title != '') AS has_title,
        (helpful_vote > 0) AS has_helpful_votes
    FROM read_json_auto(
        'C:/Users/thinkpad/Desktop/amazon-market-intelligence/collection/mcauley_reviews/Video_Games.jsonl',
        maximum_object_size=10485760
    )
""")
elapsed = time.time() - start
print(f"Video_Games done in {elapsed:.1f}s")

# 2. Load Unknown with ignore_errors
print("\nLoading Unknown (with ignore_errors)...", flush=True)
start = time.time()
con.sql("""
    INSERT INTO bronze_reviews
    SELECT 
        rating, title, text, asin, parent_asin, user_id,
        timestamp, helpful_vote, verified_purchase,
        len(images) AS image_count,
        'Unknown' AS source_category,
        (text IS NOT NULL AND text != '') AS has_text,
        (title IS NOT NULL AND title != '') AS has_title,
        (helpful_vote > 0) AS has_helpful_votes
    FROM read_json_auto(
        'C:/Users/thinkpad/Desktop/amazon-market-intelligence/collection/mcauley_reviews/Unknown.jsonl',
        maximum_object_size=10485760,
        ignore_errors=true
    )
""")
elapsed = time.time() - start
print(f"Unknown done in {elapsed:.1f}s")

# 3. Final count
total = con.sql("SELECT COUNT(*) FROM bronze_reviews").fetchone()[0]
cats = con.sql("SELECT COUNT(DISTINCT source_category) FROM bronze_reviews").fetchone()[0]
print(f"\nFINAL: {total:,} rows across {cats} categories")

con.close()
