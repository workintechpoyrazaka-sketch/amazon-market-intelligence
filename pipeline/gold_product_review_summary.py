import duckdb, time

con = duckdb.connect('C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/amazon_intelligence.duckdb')
con.sql("SET temp_directory='C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/tmp'")

# Get all categories
categories = [r[0] for r in con.sql("SELECT DISTINCT source_category FROM bronze_reviews ORDER BY 1").fetchall()]
print(f"Processing {len(categories)} categories one at a time...")

# Drop old table, create empty
con.sql("DROP TABLE IF EXISTS gold_product_review_summary")

for i, cat in enumerate(categories):
    start = time.time()
    print(f"[{i+1}/{len(categories)}] {cat}...", end=" ", flush=True)
    
    if i == 0:
        mode = "CREATE TABLE gold_product_review_summary AS"
    else:
        mode = "INSERT INTO gold_product_review_summary"
    
    con.sql(f"""
        {mode}
        SELECT
            r.parent_asin,
            r.source_category,
            COUNT(*) AS review_count,
            ROUND(AVG(r.rating), 2) AS avg_rating,
            APPROX_QUANTILE(r.rating, 0.5) AS median_rating,
            MIN(r.review_date) AS first_review_date,
            MAX(r.review_date) AS last_review_date,
            DATEDIFF('day', MIN(r.review_date), MAX(r.review_date)) AS review_span_days,
            ROUND(COUNT(*) * 1.0 / GREATEST(DATEDIFF('month', MIN(r.review_date), MAX(r.review_date)), 1), 2) AS reviews_per_month,
            SUM(CASE WHEN r.rating >= 4 THEN 1 ELSE 0 END) AS positive_count,
            SUM(CASE WHEN r.rating = 3 THEN 1 ELSE 0 END) AS neutral_count,
            SUM(CASE WHEN r.rating <= 2 THEN 1 ELSE 0 END) AS negative_count,
            ROUND(SUM(CASE WHEN r.rating >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_positive,
            ROUND(SUM(CASE WHEN r.rating <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_negative,
            ROUND(SUM(CASE WHEN r.verified_purchase THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_verified,
            ROUND(AVG(r.helpful_vote), 2) AS avg_helpful_vote,
            SUM(r.helpful_vote) AS total_helpful_votes,
            ROUND(SUM(CASE WHEN r.image_count > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_with_images,
            ROUND(AVG(CASE WHEN r.has_text THEN r.text_length END), 1) AS avg_text_length,
            COUNT(CASE WHEN r.review_date >= '2022-01-01' THEN 1 END) AS reviews_since_2022,
            ROUND(AVG(CASE WHEN r.review_date >= '2022-01-01' THEN r.rating END), 2) AS avg_rating_since_2022
        FROM silver_reviews r
        WHERE r.source_category = '{cat}'
        AND r.parent_asin IN (SELECT DISTINCT asin FROM silver_products)
        GROUP BY r.parent_asin, r.source_category
    """)
    
    elapsed = time.time() - start
    print(f"{elapsed:.0f}s")
    time.sleep(3)

result = con.sql("SELECT COUNT(*) FROM gold_product_review_summary").fetchone()[0]
print(f"\nDone! gold_product_review_summary: {result:,} total rows")
con.sql("SELECT * FROM gold_product_review_summary ORDER BY review_count DESC LIMIT 5").show()
con.close()
