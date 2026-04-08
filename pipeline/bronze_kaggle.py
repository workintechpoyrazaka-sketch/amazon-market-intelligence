"""
Bronze Layer — McAuley Metadata (35M products)
Loads all 33 category CSVs into a single DuckDB table with quality flags.
"""

import duckdbz
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'amazon_intelligence.duckdb')
CSV_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'collection', 'mcauley_csv')

def main():
    con = duckdb.connect(DB_PATH)
    start = time.time()
    
    files = sorted([f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')])
    print(f"Loading {len(files)} McAuley metadata files into Bronze...\n")
    
    for i, f in enumerate(files, 1):
        cat = f.replace('meta_', '').replace('.csv', '')
        filepath = os.path.join(CSV_FOLDER, f).replace('\\', '/')
        
        print(f"  [{i}/{len(files)}] {cat}...", end=" ", flush=True)
        t = time.time()
        
        mode = "CREATE OR REPLACE TABLE" if i == 1 else "INSERT INTO"
        
        if i == 1:
            con.sql(f"""
                CREATE OR REPLACE TABLE bronze_mcauley_metadata AS
                SELECT 
                    *,
                    CASE WHEN price IS NULL OR price = '' OR price = '—' THEN TRUE ELSE FALSE END AS flag_no_price,
                    CASE WHEN store IS NULL OR store = '' THEN TRUE ELSE FALSE END AS flag_no_store,
                    CASE WHEN details_brand IS NULL OR details_brand = '' THEN TRUE ELSE FALSE END AS flag_no_brand,
                    CASE WHEN title IS NULL OR title = '' THEN TRUE ELSE FALSE END AS flag_no_title,
                    CASE WHEN rating_number = 0 THEN TRUE ELSE FALSE END AS flag_no_ratings
                FROM read_csv_auto('{filepath}', types={{'price': 'VARCHAR'}})
            """)
        else:
            con.sql(f"""
                INSERT INTO bronze_mcauley_metadata
                SELECT 
                    *,
                    CASE WHEN price IS NULL OR price = '' OR price = '—' THEN TRUE ELSE FALSE END,
                    CASE WHEN store IS NULL OR store = '' THEN TRUE ELSE FALSE END,
                    CASE WHEN details_brand IS NULL OR details_brand = '' THEN TRUE ELSE FALSE END,
                    CASE WHEN title IS NULL OR title = '' THEN TRUE ELSE FALSE END,
                    CASE WHEN rating_number = 0 THEN TRUE ELSE FALSE END
                FROM read_csv_auto('{filepath}', types={{'price': 'VARCHAR'}})
            """)
        
        elapsed = time.time() - t
        print(f"{elapsed:.1f}s")
    
    # Verify
    total = con.sql("SELECT COUNT(*) FROM bronze_mcauley_metadata").fetchone()[0]
    cats = con.sql("SELECT COUNT(DISTINCT main_category) FROM bronze_mcauley_metadata").fetchone()[0]
    flagged = con.sql("""
        SELECT 
            SUM(CASE WHEN flag_no_price THEN 1 ELSE 0 END) as no_price,
            SUM(CASE WHEN flag_no_store THEN 1 ELSE 0 END) as no_store,
            SUM(CASE WHEN flag_no_brand THEN 1 ELSE 0 END) as no_brand,
            SUM(CASE WHEN flag_no_ratings THEN 1 ELSE 0 END) as no_ratings
        FROM bronze_mcauley_metadata
    """).fetchone()
    
    elapsed = time.time() - start
    print(f"\n  Total: {total:,} rows, {cats} categories in {elapsed:.0f}s")
    print(f"  Flagged — no_price: {flagged[0]:,} | no_store: {flagged[1]:,} | no_brand: {flagged[2]:,} | no_ratings: {flagged[3]:,}")
    print("  Done.")
    
    con.close()

if __name__ == "__main__":
    main()