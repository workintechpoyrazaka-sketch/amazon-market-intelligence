import duckdb

con = duckdb.connect('C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/amazon_intelligence.duckdb')

print("=== silver_products coverage ===")
con.sql("""
    SELECT 
        COUNT(*) AS total,
        COUNT(CASE WHEN listPrice > 0 THEN 1 END) AS has_listprice,
        SUM(CAST(is_best_seller AS INT)) AS bestsellers,
        SUM(has_features) AS has_features,
        SUM(has_description) AS has_description,
        COUNT(CASE WHEN title IS NOT NULL THEN 1 END) AS has_title
    FROM silver_products
""").show()

print("\n=== bought_together in bronze_mcauley? ===")
cols = [r[0] for r in con.sql("DESCRIBE bronze_mcauley_metadata").fetchall()]
print("Has bought_together:", "bought_together" in cols)
if "bought_together" in cols:
    con.sql("""
        SELECT 
            COUNT(*) AS total,
            COUNT(CASE WHEN bought_together IS NOT NULL THEN 1 END) AS has_bt
        FROM bronze_mcauley_metadata
    """).show()

print("\n=== bronze_reviews by category (top 10) ===")
con.sql("""
    SELECT source_category, COUNT(*) AS cnt 
    FROM bronze_reviews 
    GROUP BY 1 ORDER BY 2 DESC 
    LIMIT 10
""").show()

con.close()
