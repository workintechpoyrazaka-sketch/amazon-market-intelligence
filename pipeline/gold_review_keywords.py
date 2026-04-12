import duckdb, time
con = duckdb.connect('C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/amazon_intelligence.duckdb')
con.sql("SET temp_directory='C:/Users/thinkpad/Desktop/amazon-market-intelligence/data/tmp'")
print("Creating gold_review_keywords... (title word frequency, sampled)")
start = time.time()

stopwords = "a,an,the,and,or,but,in,on,at,to,for,of,with,by,from,is,it,was,are,were,be,been,this,that,these,those,i,my,me,we,our,you,your,he,she,they,them,their,its,not,no,do,did,does,have,has,had,will,would,can,could,should,so,if,just,very,too,also,than,then,more,most,all,any,some,such,only,other,one,two,each,about,up,out,into,over,after,how,what,when,where,which,who,why,as,both,few,many,much,own,same,well"
stopword_list = ",".join([f"'{w.strip()}'" for w in stopwords.split(",")])

con.sql(f"""
    CREATE OR REPLACE TABLE gold_review_keywords AS
    WITH sampled AS (
        SELECT source_category, title, rating
        FROM silver_reviews
        WHERE has_title
        USING SAMPLE 10 PERCENT (bernoulli)
    ),
    words AS (
        SELECT 
            source_category,
            CASE WHEN rating >= 4 THEN 'positive' WHEN rating <= 2 THEN 'negative' ELSE 'neutral' END AS sentiment,
            LOWER(TRIM(word)) AS word
        FROM sampled, 
        LATERAL UNNEST(string_split(regexp_replace(LOWER(title), '[^a-z0-9 ]', ' ', 'g'), ' ')) AS t(word)
        WHERE TRIM(word) != '' AND LENGTH(TRIM(word)) > 2
        AND LOWER(TRIM(word)) NOT IN ({stopword_list})
    )
    SELECT 
        source_category,
        sentiment,
        word,
        COUNT(*) AS word_count
    FROM words
    GROUP BY source_category, sentiment, word
    HAVING COUNT(*) >= 50
    ORDER BY source_category, sentiment, word_count DESC
""")
elapsed = time.time() - start
result = con.sql("SELECT COUNT(*) FROM gold_review_keywords").fetchone()[0]
print(f"gold_review_keywords: {result:,} rows in {elapsed/60:.1f} min")
print("\nTop negative keywords in Electronics:")
con.sql("""
    SELECT word, word_count 
    FROM gold_review_keywords 
    WHERE source_category = 'Electronics' AND sentiment = 'negative'
    ORDER BY word_count DESC
    LIMIT 10
""").show()
con.close()
