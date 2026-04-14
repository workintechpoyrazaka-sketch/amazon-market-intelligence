# Methodology

## Project Overview

Amazon Market Intelligence is an end-to-end data pipeline and intelligence tool built to answer a single question: **what actually drives product success on Amazon?**

The project processes 200+ GB of raw data — 1.4M Kaggle products, 35M McAuley metadata records, and 526M customer reviews across 33 categories — through a Bronze→Silver→Gold medallion pipeline, extracts 100 analytical findings, trains 3 ML models, and delivers results through a 5-mode interactive Streamlit tool.

## Data Sources

**Kaggle Amazon Products (1.4M products, ~300 MB):** Product listings with prices, ratings, review counts, monthly sales (`boughtInLastMonth`), Best Seller badge status, and subcategory classification across 248 subcategories. This is the only source with sales volume data, making it the revenue backbone.

**Kaggle Amazon Categories (248 rows, <1 MB):** Subcategory taxonomy used for category-level aggregations.

**McAuley Amazon Metadata (35M products, ~37 GB, HuggingFace):** Product metadata including store names, brand, manufacturer, features, descriptions, and category tags across 33 category CSV files. Enriches Kaggle products with seller and listing quality signals. 50 distinct `main_category` values found inside 33 files — products are tagged with categories outside their source file.

**McAuley Amazon Reviews (526M reviews, ~170-200 GB, HuggingFace):** Individual review records with rating, timestamp, review text, user ID, product ID, verified purchase flag, helpful votes, and image count. Downloaded as 33 JSONL files, one per category. `Unknown.jsonl` had corruption at line 19.6M — loaded with `ignore_errors=true`.

## Pipeline Architecture

### Engine: DuckDB

The project started on BigQuery but migrated to DuckDB after hitting free-tier storage quotas twice. DuckDB runs locally on a ThinkPad E16 Gen 2, handles 200+ GB without cloud dependency, and provides a stronger portfolio signal: "I optimized the query, not the infrastructure."

DuckDB is single-process — the database file can only be opened by one connection at a time. Long-running downloads and pipeline scripts required separate terminals with careful coordination.

### Medallion Pipeline

**Bronze (4 tables):** Raw data loaded with minimal transformation. All rows kept, quality flags added. The principle: flag, don't filter. Bronze reviews stored as TABLE (not VIEW) because 526M rows are queried heavily for NLP, sentiment, and temporal analysis — one-time JSONL parsing cost pays off versus re-reading 33 files on every query.

**Silver (5 tables/views):** Cleaned, standardized, and enriched data at natural grain.

- `silver_products` (TABLE, 1.4M rows): Kaggle products joined 1:1 with McAuley metadata. 28.5% match rate (406K of 1.4M). Snake_case column names, type-safe casts, NULL handling.
- `silver_products_full` (VIEW, ~32.6M rows): Full McAuley ecosystem for seller landscape analysis. VIEW because 35M-row CREATE TABLE took 15+ minutes with no analytical benefit — VIEW gives identical SQL at zero disk cost.
- `silver_stores` (TABLE, 4.77M rows): Store-level aggregation from McAuley metadata. TABLE because GROUP BY reduces 35M to 4.77M — significant reduction justifies materialization.
- `silver_categories` (TABLE, 50 rows): Reconciled category taxonomy.
- `silver_reviews` (VIEW, 526M rows): Column transforms on bronze_reviews. VIEW because output ≈ input size.

**Gold (18 tables):** Pre-aggregated analytical tables, each serving a specific tool mode or analysis dimension. Bronze keeps everything, Silver cleans everything, Gold aggregates only what the consumer (Streamlit tool) needs.

Product-level Gold tables filter to the 1.4M Kaggle products via `WHERE parent_asin IN (SELECT DISTINCT asin FROM silver_products)` — this was the architectural breakthrough that reduced 526M-row scans to manageable subsets and prevented thermal shutdown.

### Key Architectural Decisions

**VIEW vs TABLE rule:** VIEW when output ≈ input size (column transforms, filters), TABLE when output << input (aggregations). A 35M-row VIEW is instant and costs zero disk; a GROUP BY from 35M to 500K rows is worth the one-time materialization cost.

**Two-granularity design:** 73% of Kaggle products have NULL `main_category` (only 381K of 1.4M matched McAuley). Majority-vote mapping was evaluated and rejected — 242 of 247 subcategories had conflicting majority categories, worst majority at only 21.8%. Solution: two Gold landscape tables, subcategory (248 rows, full 1.4M revenue coverage) and main_category (50 rows, full 35M ecosystem). The tool supports both zoom levels.

**Batch-by-category processing:** Heavy review aggregations (526M rows with millions of groups) caused thermal shutdown and coil whine on sustained load. Solution: process one `source_category` at a time with 3-second sleep between batches. 33 batches × 1-2 minutes each instead of one 5-hour scan.

**APPROX_QUANTILE over MEDIAN:** MEDIAN on 526M rows with millions of groups requires sorting each group — hours of CPU time. APPROX_QUANTILE is 99.9% accurate and 10× faster. On a 1-5 rating scale, the difference is analytically invisible.

**Revenue estimation:** `price × boughtInLastMonth`. An approximation, but valuable — few public datasets have any sales volume signal at all.

## Analysis Approach

### 8 Notebooks, 90 Charts, 100 Findings

Five exploratory notebooks (Category Landscape, Pricing & Discounts, Brand & Listing Quality, Store & Seller Patterns, Reviews & Sentiment) and three ML notebooks (Competitive Clustering, Success Factor Discovery, Review Anomaly Detection).

**Schema discovery first:** Every notebook starts by running DESCRIBE on all Gold tables it will use. Column names are never guessed. This rule saved an estimated 30+ minutes of debugging per notebook.

**Keyword analysis: ratios over frequency.** Raw word frequency in reviews shows generic words ("product", "good"). The distinctive ratio — negative count ÷ positive count — surfaces real complaint signals: "inedible" (699×), "rancid" (396×), "unsafe" (226×). Same approach inverted for praise keywords.

### ML Models

**K-Means Competitive Clustering (NB08):** Segments products into 5 archetypes using category-relative features (PERCENT_RANK within subcategory). Silhouette scores were flat (0.18-0.22) for k=3-10 — math didn't pick a winner. k=5 chosen by business interpretability: the archetypes are actionable for sellers. Features: price rank, sales rank, reviews rank, rating, title length rank, best seller status.

**XGBoost Success Factor Discovery (NB09):** Binary classification — top 25% revenue within subcategory (NTILE(4)). Only listing-visible attributes used as features. `bought_last_month` and `estimated_revenue` excluded to prevent data leakage. AUC 0.78 — listing-visible features predict 78% of success variance; the remaining 22% is marketplace randomness (advertising, timing, external demand). SHAP analysis reveals price positioning within category as the #1 predictor (0.62 mean |SHAP|, 3× any other feature).

**Isolation Forest Review Anomaly Detection (NB10):** Unsupervised — no labeled "fake" reviews exist. 5% contamination rate, 12 review pattern features, minimum 5 reviews per product. Flags 14,620 of 292K products. The suspicious profile: low verified rate (54.5% vs 93.5% normal), burst review velocity (6.7× higher), and a reversed unverified 5-star gap (+2.8 vs −8.6 market-wide). Suspicious reviews are longer (413 vs 172 chars) — organized campaigns write full text, not short bot spam.

## Tool Design

The Streamlit app has 5 modes answering 11 customer questions. Every query hits pre-aggregated Gold tables — the tool never scans raw Bronze/Silver data. Health Check mode loads the XGBoost model for individual product SHAP diagnosis.

Deployment uses dual-mode data loading: local DuckDB file for development, Parquet files loaded into in-memory DuckDB for Streamlit Cloud. Gold tables export to ~110 MB of compressed Parquet.

## Limitations

- Revenue estimation uses `price × boughtInLastMonth` — an approximation, not actual Amazon revenue data
- Clothing categories have ~1% review match rate due to McAuley `parent_asin` vs Kaggle `asin` mismatch
- NLP sentiment is rating-based proxy in Gold tables; VADER analysis available in notebooks on sampled subsets
- English-only NLP (VADER/TextBlob only reliable on English), though "excelente" at 67K uses suggests significant Spanish-speaking reviewer base
- Geographic analysis not possible — no geo data in any source
- Bundle/cross-sell analysis cut — `bought_together` field not present in bronze data
