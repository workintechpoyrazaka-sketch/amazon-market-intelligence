"""Bronze layer: Kaggle categories (248 subcategories)."""
import duckdb

con = duckdb.connect('data/amazon_intelligence.duckdb')

con.sql("""
    CREATE OR REPLACE TABLE bronze_kaggle_categories AS
    SELECT
        id,
        category_name,
        -- Quality flags
        CASE WHEN category_name IS NULL OR TRIM(category_name) = '' THEN 1 ELSE 0 END AS flag_missing_name,
        LENGTH(TRIM(category_name)) AS name_length
    FROM read_csv_auto('collection/amazon_categories.csv')
""")

result = con.sql("SELECT COUNT(*) AS rows FROM bronze_kaggle_categories").fetchone()
print(f"bronze_kaggle_categories: {result[0]} rows loaded")

con.close()
