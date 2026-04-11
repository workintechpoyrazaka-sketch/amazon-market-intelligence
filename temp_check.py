import duckdb
con = duckdb.connect('data/amazon_intelligence.duckdb')
rows = con.sql("""
    WITH ranked AS (
        SELECT 
            subcategory, 
            main_category, 
            COUNT(*) AS cnt,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY subcategory), 1) AS pct,
            ROW_NUMBER() OVER (PARTITION BY subcategory ORDER BY COUNT(*) DESC) AS rn
        FROM silver_products 
        WHERE main_category IS NOT NULL 
        GROUP BY subcategory, main_category
    )
    SELECT pct FROM ranked WHERE rn = 1 ORDER BY pct ASC LIMIT 20
""").fetchall()
for r in rows:
    print(r[0])
con.close()
