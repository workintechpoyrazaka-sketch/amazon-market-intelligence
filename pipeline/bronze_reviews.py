import duckdb
import os
import time

con = duckdb.connect('C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/amazon_intelligence.duckdb')
reviews_dir = 'C:/Users/thinkpad/Desktop/amazon-market-intelligence/collection/mcauley_reviews'

# Get all JSONL files
files = sorted([f for f in os.listdir(reviews_dir) if f.endswith('.jsonl')])
print(f"Found {len(files)} review files\n")

total_rows = 0
total_start = time.time()

for i, filename in enumerate(files):
    filepath = os.path.join(reviews_dir, filename).replace('\\', '/')
    category = filename.replace('.jsonl', '')
    
    start = time.time()
    print(f"[{i+1}/{len(files)}] {category}...", end=' ', flush=True)
    
    sql = f"""
        {'CREATE OR REPLACE TABLE bronze_reviews AS' if i == 0 else 'INSERT INTO bronze_reviews'}
        SELECT 
            rating,
            title,
            text,
            asin,
            parent_asin,
            user_id,
            timestamp,
            helpful_vote,
            verified_purchase,
            len(images) AS image_count,
            '{category}' AS source_category,
            -- Quality flags
            (text IS NOT NULL AND text != '') AS has_text,
            (title IS NOT NULL AND title != '') AS has_title,
            (helpful_vote > 0) AS has_helpful_votes
        FROM read_json_auto(
            '{filepath}',
            maximum_object_size=10485760
        )
    """
    
    con.sql(sql)
    
    count = con.sql(f"SELECT COUNT(*) FROM bronze_reviews WHERE source_category = '{category}'").fetchone()[0]
    elapsed = time.time() - start
    total_rows += count
    print(f"{count:>12,} rows  |  {elapsed:.1f}s  |  Running total: {total_rows:,}")

total_elapsed = time.time() - total_start
print(f"\n{'='*60}")
print(f"DONE. {total_rows:,} total rows in {total_elapsed/60:.1f} minutes")
print(f"Average rate: {total_rows/total_elapsed:,.0f} rows/sec")

con.close()
