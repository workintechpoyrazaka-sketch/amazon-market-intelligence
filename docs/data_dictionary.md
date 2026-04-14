# Data Dictionary

## Overview

The Amazon Market Intelligence database contains 4 Bronze tables, 5 Silver tables/views, and 18 Gold tables organized in a medallion architecture. All tables live in a single DuckDB file (`data/amazon_intelligence.duckdb`). For cloud deployment, Gold tables and `silver_products` are exported as Parquet files.

---

## Bronze Layer — Raw Data

### bronze_kaggle_products
**Rows:** 1,426,337 | **Type:** TABLE | **Source:** Kaggle Amazon Products dataset

| Column | Type | Description |
|--------|------|-------------|
| asin | VARCHAR | Amazon Standard Identification Number (unique product ID) |
| title | VARCHAR | Product listing title |
| imgUrl | VARCHAR | Product image URL |
| productURL | VARCHAR | Amazon product page URL |
| stars | DECIMAL | Star rating (1.0–5.0) |
| reviews | INTEGER | Number of customer reviews |
| price | DECIMAL | Current listing price (USD) |
| listPrice | DECIMAL | Original list price before discount |
| categoryName | VARCHAR | Subcategory name (248 distinct values) |
| isBestSeller | BOOLEAN | Amazon Best Seller badge status |
| boughtInLastMonth | INTEGER | Units sold in the last month (0 or 50+, no values 1-49) |

### bronze_mcauley_metadata
**Rows:** 35,003,183 | **Type:** TABLE | **Source:** McAuley Lab, HuggingFace (33 CSV files)

| Column | Type | Description |
|--------|------|-------------|
| parent_asin | VARCHAR | Parent ASIN (product group ID) |
| title | VARCHAR | Product title |
| main_category | VARCHAR | Main category (50 distinct values across 33 source files) |
| price | VARCHAR | Price as string — em-dash "—" used as NULL |
| average_rating | DECIMAL | Average star rating |
| rating_number | INTEGER | Number of ratings |
| store | VARCHAR | Seller store name |
| brand | VARCHAR | Brand name (62% NULL overall) |
| features | VARCHAR | Product feature bullet points |
| description | VARCHAR | Product description text |
| categories | VARCHAR | Category hierarchy |

### bronze_kaggle_categories
**Rows:** 248 | **Type:** TABLE | **Source:** Kaggle Amazon Categories dataset

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Category ID |
| category_name | VARCHAR | Subcategory name |

### bronze_reviews
**Rows:** 526,840,325 | **Type:** TABLE | **Source:** McAuley Lab, HuggingFace (33 JSONL files)

| Column | Type | Description |
|--------|------|-------------|
| parent_asin | VARCHAR | Product ASIN this review belongs to |
| user_id | VARCHAR | Reviewer user ID |
| rating | DECIMAL | Star rating (1.0–5.0) |
| title | VARCHAR | Review title/headline |
| text | VARCHAR | Review body text |
| timestamp | BIGINT | Unix timestamp of review |
| verified_purchase | BOOLEAN | Whether reviewer bought the product |
| helpful_vote | INTEGER | Number of helpful votes received |
| image_count | INTEGER | Number of images attached (derived from `len(images)`) |
| source_category | VARCHAR | Category file the review was loaded from (33 values) |

---

## Silver Layer — Cleaned & Enriched

### silver_products
**Rows:** 1,426,337 | **Type:** TABLE | **Grain:** One row per Kaggle product

| Column | Type | Description |
|--------|------|-------------|
| asin | VARCHAR | Product ASIN (primary key) |
| title | VARCHAR | Product title |
| price | DECIMAL | Current price (USD) |
| rating | DECIMAL | Average star rating |
| review_count | INTEGER | Number of reviews |
| bought_last_month | INTEGER | Monthly sales volume |
| estimated_revenue | DECIMAL | `price × bought_last_month` |
| is_best_seller | BOOLEAN | Best Seller badge |
| subcategory | VARCHAR | Subcategory (248 values, 100% coverage) |
| main_category | VARCHAR | Main category from McAuley match (NULL for 73%) |
| discount_pct | DECIMAL | Discount percentage from list price |
| brand | VARCHAR | Brand name (from McAuley, NULL if unmatched) |
| store | VARCHAR | Store name (from McAuley) |
| features | VARCHAR | Feature bullet points (from McAuley) |
| description | VARCHAR | Product description (from McAuley) |

*28.5% of products matched McAuley metadata (406K of 1.4M). Unmatched products have NULL for brand, store, features, description.*

### silver_products_full
**Rows:** ~32.6M | **Type:** VIEW | **Grain:** One row per McAuley product

Full 35M McAuley ecosystem with standardized columns. VIEW because output ≈ input — no analytical benefit to materializing. Filtered to exclude 2.3M rows with NULL `main_category`.

### silver_stores
**Rows:** 4,771,001 | **Type:** TABLE | **Grain:** One row per store

| Column | Type | Description |
|--------|------|-------------|
| store | VARCHAR | Store name (primary key) |
| product_count | INTEGER | Number of products listed |
| category_count | INTEGER | Distinct categories sold in |
| brand_count | INTEGER | Distinct brands carried |
| avg_rating | DECIMAL | Average product rating |
| avg_reviews | INTEGER | Average review count per product |

### silver_categories
**Rows:** 50 | **Type:** TABLE | **Grain:** One row per main category

Reconciled category taxonomy from 50 distinct `main_category` values found across 33 source files.

### silver_reviews
**Rows:** 526,840,325 | **Type:** VIEW | **Grain:** One row per review

Column transforms on `bronze_reviews`. VIEW because output ≈ input.

---

## Gold Layer — Analytical Aggregations

### gold_subcategory_landscape
**Rows:** 248 | **Grain:** One row per subcategory | **Tool Mode:** Category Scout

| Column | Type | Description |
|--------|------|-------------|
| subcategory | VARCHAR | Subcategory name |
| product_count | INTEGER | Total products in subcategory |
| avg_price | DECIMAL | Mean product price |
| median_price | DECIMAL | Median product price |
| avg_rating | DECIMAL | Mean star rating |
| avg_reviews | DECIMAL | Mean review count |
| total_units_sold | BIGINT | Sum of `bought_last_month` |
| total_revenue | DECIMAL | Sum of `estimated_revenue` |
| avg_revenue_per_product | DECIMAL | Revenue efficiency metric |
| pct_best_sellers | DECIMAL | Percentage with Best Seller badge |
| pct_active | DECIMAL | Percentage with `bought_last_month > 0` |
| pct_zero_reviews | DECIMAL | Percentage with zero reviews |
| avg_discount_pct | DECIMAL | Mean discount percentage |
| pct_with_brand | DECIMAL | Percentage with brand name |
| pct_with_features | DECIMAL | Percentage with feature bullets |
| pct_with_description | DECIMAL | Percentage with description |
| pct_with_store | DECIMAL | Percentage with store name |

### gold_main_category_landscape
**Rows:** 50 | **Grain:** One row per main category | **Tool Mode:** Category Scout

| Column | Type | Description |
|--------|------|-------------|
| main_category | VARCHAR | Main category name |
| ecosystem_products | INTEGER | Products in full 35M McAuley ecosystem |
| store_count | INTEGER | Distinct stores |
| brand_count | INTEGER | Distinct brands |
| kaggle_products | INTEGER | Matched Kaggle products |
| kaggle_coverage_pct | DECIMAL | Kaggle match percentage |
| total_units_sold | BIGINT | Sales volume (Kaggle-matched only) |
| total_revenue | DECIMAL | Revenue (Kaggle-matched only) |
| avg_revenue_per_product | DECIMAL | Revenue per Kaggle product |
| avg_price | DECIMAL | Mean price |
| avg_rating | DECIMAL | Mean rating |
| pct_active | DECIMAL | Active product percentage |
| products_per_store | DECIMAL | Density: products ÷ stores |
| revenue_per_store | DECIMAL | Revenue efficiency per store |
| pct_with_features | DECIMAL | Feature coverage |
| pct_with_description | DECIMAL | Description coverage |
| pct_with_brand | DECIMAL | Brand coverage |
| pct_with_store | DECIMAL | Store coverage |

### gold_temporal_trends
**Rows:** 8,721 | **Grain:** One row per category × year × month | **Tool Mode:** Category Scout, Voice of Customer

| Column | Type | Description |
|--------|------|-------------|
| source_category | VARCHAR | Category (33 McAuley categories) |
| review_year | INTEGER | Year |
| review_month | INTEGER | Month |
| review_count | INTEGER | Reviews in this period |
| avg_rating | DECIMAL | Mean rating |
| median_rating | DECIMAL | Median rating |
| pct_verified | DECIMAL | Verified purchase percentage |
| pct_with_images | DECIMAL | Reviews with images |
| avg_helpful_votes | DECIMAL | Mean helpful votes |
| avg_text_length | DECIMAL | Mean review text length |
| negative_reviews | INTEGER | Rating ≤ 2 count |
| neutral_reviews | INTEGER | Rating = 3 count |
| positive_reviews | INTEGER | Rating ≥ 4 count |
| pct_negative | DECIMAL | Negative review percentage |

### gold_price_positioning
**Rows:** 1,229 | **Grain:** One row per subcategory × price tier | **Tool Mode:** Competitive Positioning

| Column | Type | Description |
|--------|------|-------------|
| subcategory | VARCHAR | Subcategory |
| price_tier | VARCHAR | Budget / Low / Mid / Premium / Luxury |
| product_count | INTEGER | Products in tier |
| avg_price | DECIMAL | Mean price |
| median_price | DECIMAL | Median price |
| avg_rating | DECIMAL | Mean rating |
| avg_reviews | DECIMAL | Mean review count |
| total_units_sold | BIGINT | Sales volume |
| total_revenue | DECIMAL | Revenue |
| avg_revenue_per_product | DECIMAL | Revenue efficiency |
| pct_active | DECIMAL | Active percentage |
| pct_best_sellers | DECIMAL | Best Seller percentage |
| avg_discount_pct | DECIMAL | Mean discount |
| pct_branded | DECIMAL | Branded percentage |
| avg_title_length | DECIMAL | Mean title character length |
| pct_with_features | DECIMAL | Feature coverage |

### gold_discount_effectiveness
**Rows:** 807 | **Grain:** One row per subcategory × discount tier | **Tool Mode:** Competitive Positioning

| Column | Type | Description |
|--------|------|-------------|
| subcategory | VARCHAR | Subcategory |
| discount_tier | VARCHAR | No Discount / Light (1-19%) / Medium (20-49%) / Deep (50%+) |
| product_count | INTEGER | Products in tier |
| avg_discount | DECIMAL | Mean discount percentage |
| avg_price | DECIMAL | Mean price |
| avg_rating | DECIMAL | Mean rating |
| avg_reviews | DECIMAL | Mean review count |
| total_units_sold | BIGINT | Sales volume |
| total_revenue | DECIMAL | Revenue |
| avg_revenue_per_product | DECIMAL | Revenue efficiency |
| pct_active | DECIMAL | Active percentage |
| pct_best_sellers | DECIMAL | Best Seller percentage |

### gold_brand_dynamics
**Rows:** 491 | **Grain:** One row per subcategory × brand status | **Tool Mode:** Competitive Positioning

| Column | Type | Description |
|--------|------|-------------|
| subcategory | VARCHAR | Subcategory |
| brand_status | VARCHAR | Branded / Unbranded |
| product_count | INTEGER | Products |
| avg_price | DECIMAL | Mean price |
| avg_rating | DECIMAL | Mean rating |
| avg_reviews | DECIMAL | Mean review count |
| total_units_sold | BIGINT | Sales volume |
| total_revenue | DECIMAL | Revenue |
| avg_revenue_per_product | DECIMAL | Revenue efficiency |
| pct_active | DECIMAL | Active percentage |
| pct_best_sellers | DECIMAL | Best Seller percentage |
| avg_discount_pct | DECIMAL | Mean discount |

### gold_listing_quality
**Rows:** 248 | **Grain:** One row per subcategory | **Tool Mode:** Competitive Positioning

| Column | Type | Description |
|--------|------|-------------|
| subcategory | VARCHAR | Subcategory |
| product_count | INTEGER | Total products |
| avg_title_length | DECIMAL | Mean title character length |
| median_title_length | DECIMAL | Median title length |
| pct_with_features | DECIMAL | % with feature bullets |
| pct_with_description | DECIMAL | % with description |
| pct_with_brand | DECIMAL | % with brand |
| pct_with_store | DECIMAL | % with store |
| avg_rev_with_features | DECIMAL | Avg revenue — products WITH features |
| avg_rev_without_features | DECIMAL | Avg revenue — products WITHOUT features |
| avg_rev_with_description | DECIMAL | Avg revenue — WITH description |
| avg_rev_without_description | DECIMAL | Avg revenue — WITHOUT description |
| avg_rev_with_brand | DECIMAL | Avg revenue — WITH brand |
| avg_rev_without_brand | DECIMAL | Avg revenue — WITHOUT brand |
| avg_rev_short_title | DECIMAL | Avg revenue — short titles |
| avg_rev_medium_title | DECIMAL | Avg revenue — medium titles |
| avg_rev_long_title | DECIMAL | Avg revenue — long titles |
| avg_rev_very_long_title | DECIMAL | Avg revenue — very long titles |
| avg_completeness_score | DECIMAL | Average listing completeness (0-100) |
| avg_rev_high_completeness | DECIMAL | Avg revenue — high completeness |
| avg_rev_low_completeness | DECIMAL | Avg revenue — low completeness |

### gold_bestseller_analysis
**Rows:** 248 | **Grain:** One row per subcategory | **Tool Mode:** Health Check

| Column | Type | Description |
|--------|------|-------------|
| subcategory | VARCHAR | Subcategory |
| total_products | INTEGER | All products |
| bestseller_count | INTEGER | Products with badge |
| pct_bestsellers | DECIMAL | Badge percentage |
| avg_price_bestseller | DECIMAL | Avg price — Best Sellers |
| avg_price_non_bestseller | DECIMAL | Avg price — non-Best Sellers |
| avg_rating_bestseller | DECIMAL | Avg rating — Best Sellers |
| avg_rating_non_bestseller | DECIMAL | Avg rating — non-Best Sellers |
| avg_reviews_bestseller | DECIMAL | Avg reviews — Best Sellers |
| avg_reviews_non_bestseller | DECIMAL | Avg reviews — non-Best Sellers |
| avg_rev_bestseller | DECIMAL | Avg revenue — Best Sellers |
| avg_rev_non_bestseller | DECIMAL | Avg revenue — non-Best Sellers |
| avg_sales_bestseller | DECIMAL | Avg sales — Best Sellers |
| avg_sales_non_bestseller | DECIMAL | Avg sales — non-Best Sellers |
| pct_revenue_from_bestsellers | DECIMAL | Revenue share from badge holders |
| bestseller_revenue_multiplier | DECIMAL | Revenue ratio: badge ÷ no badge |

### gold_product_benchmarks
**Rows:** 248 | **Grain:** One row per subcategory | **Tool Mode:** Health Check

Subcategory-level percentile benchmarks for product comparison.

### gold_category_benchmarks_full
**Rows:** 248 | **Grain:** One row per subcategory | **Tool Mode:** Health Check

Extended benchmarks joining product review summary statistics to subcategory aggregations.

### gold_store_performance
**Rows:** ~92,656 | **Grain:** One row per store (Kaggle-matched) | **Tool Mode:** Health Check

| Column | Type | Description |
|--------|------|-------------|
| store | VARCHAR | Store name |
| store_type | VARCHAR | Specialist / Focused / Generalist |
| ecosystem_products | INTEGER | Products in full McAuley ecosystem |
| category_count | INTEGER | Categories sold in |
| brand_count | INTEGER | Brands carried |
| ecosystem_avg_rating | DECIMAL | Rating across all ecosystem products |
| ecosystem_avg_reviews | INTEGER | Reviews across ecosystem |
| kaggle_products | INTEGER | Kaggle-matched products |
| avg_price | DECIMAL | Mean price (Kaggle) |
| total_revenue | DECIMAL | Total revenue (Kaggle) |
| avg_revenue_per_product | DECIMAL | Revenue efficiency |
| total_units_sold | BIGINT | Sales volume |
| pct_active | DECIMAL | Active product percentage |
| avg_rating | DECIMAL | Mean rating (Kaggle) |
| avg_reviews | DECIMAL | Mean reviews (Kaggle) |

*Store types: Specialist (1 category), Focused (2-5 categories), Generalist (6+ categories)*

### gold_review_sentiment
**Rows:** 33 | **Grain:** One row per source category | **Tool Mode:** Voice of Customer

| Column | Type | Description |
|--------|------|-------------|
| source_category | VARCHAR | Category |
| total_reviews | BIGINT | Total review count |
| avg_rating | DECIMAL | Mean rating |
| median_rating | DECIMAL | Median rating |
| positive_count | BIGINT | Rating ≥ 4 |
| neutral_count | BIGINT | Rating = 3 |
| negative_count | BIGINT | Rating ≤ 2 |
| pct_positive | DECIMAL | Positive percentage |
| pct_neutral | DECIMAL | Neutral percentage |
| pct_negative | DECIMAL | Negative percentage |
| pct_with_text | DECIMAL | % with review text |
| avg_text_length | DECIMAL | Mean text length (all) |
| avg_text_length_negative | DECIMAL | Mean text length (negative) |
| avg_text_length_positive | DECIMAL | Mean text length (positive) |
| negative_verbosity_ratio | DECIMAL | Negative ÷ positive text length |
| avg_helpful_negative | DECIMAL | Mean helpful votes (negative) |
| avg_helpful_positive | DECIMAL | Mean helpful votes (positive) |
| pct_images_negative | DECIMAL | % with images (negative) |
| pct_images_positive | DECIMAL | % with images (positive) |

### gold_review_keywords
**Rows:** 165,858 | **Grain:** One row per category × sentiment × word | **Tool Mode:** Voice of Customer

| Column | Type | Description |
|--------|------|-------------|
| source_category | VARCHAR | Category |
| sentiment | VARCHAR | positive / negative |
| word | VARCHAR | Individual keyword |
| word_count | INTEGER | Frequency in sentiment group |

*Built from 10% stratified sample. Distinctive ratios (neg÷pos, pos÷neg) computed in analysis notebooks.*

### gold_product_review_summary
**Rows:** 419,016 | **Grain:** One row per product | **Tool Mode:** Competitive Positioning

| Column | Type | Description |
|--------|------|-------------|
| parent_asin | VARCHAR | Product ASIN |
| source_category | VARCHAR | Category |
| review_count | INTEGER | Total reviews |
| avg_rating | DECIMAL | Mean rating |
| median_rating | DECIMAL | Median rating |
| first_review_date | DATE | Earliest review |
| last_review_date | DATE | Most recent review |
| review_span_days | INTEGER | Days between first and last review |
| reviews_per_month | DECIMAL | Monthly review velocity |
| positive_count | INTEGER | Positive reviews |
| neutral_count | INTEGER | Neutral reviews |
| negative_count | INTEGER | Negative reviews |
| pct_positive | DECIMAL | Positive percentage |
| pct_negative | DECIMAL | Negative percentage |
| pct_verified | DECIMAL | Verified purchase percentage |
| avg_helpful_vote | DECIMAL | Mean helpful votes |
| total_helpful_votes | INTEGER | Sum of helpful votes |
| pct_with_images | DECIMAL | % with images |
| avg_text_length | DECIMAL | Mean review text length |
| reviews_since_2022 | INTEGER | Reviews from 2022 onward |
| avg_rating_since_2022 | DECIMAL | Recent rating trend |

### gold_product_review_trust
**Rows:** 419,016 | **Grain:** One row per product | **Tool Mode:** Review Trust Score

| Column | Type | Description |
|--------|------|-------------|
| parent_asin | VARCHAR | Product ASIN |
| source_category | VARCHAR | Category |
| review_count | INTEGER | Total reviews |
| unique_reviewers | INTEGER | Distinct reviewers |
| reviews_per_reviewer | DECIMAL | Avg reviews per reviewer |
| pct_extreme_ratings | DECIMAL | % rated 1 or 5 |
| pct_5star | DECIMAL | 5-star percentage |
| pct_1star | DECIMAL | 1-star percentage |
| pct_verified | DECIMAL | Verified purchase percentage |
| pct_5star_unverified | DECIMAL | 5-star rate among unverified |
| pct_5star_verified | DECIMAL | 5-star rate among verified |
| pct_with_text | DECIMAL | % with review text |
| avg_text_length | DECIMAL | Mean text length |
| pct_very_short_text | DECIMAL | % with very short text |
| reviews_per_day | DECIMAL | Daily review velocity |
| pct_with_helpful_votes | DECIMAL | % receiving helpful votes |

### gold_review_trust
**Rows:** 33 | **Grain:** One row per source category | **Tool Mode:** Review Trust Score

| Column | Type | Description |
|--------|------|-------------|
| source_category | VARCHAR | Category |
| total_reviews | BIGINT | Total reviews |
| unique_reviewers | BIGINT | Distinct reviewers |
| reviews_per_reviewer | DECIMAL | Avg reviews per reviewer |
| pct_verified | DECIMAL | Verified purchase percentage |
| pct_unverified | DECIMAL | Unverified percentage |
| pct_with_images | DECIMAL | % with images |
| pct_with_text | DECIMAL | % with text |
| avg_helpful_votes | DECIMAL | Mean helpful votes |
| avg_text_length | DECIMAL | Mean text length |
| pct_5star | DECIMAL | 5-star percentage |
| pct_4star | DECIMAL | 4-star percentage |
| pct_3star | DECIMAL | 3-star percentage |
| pct_2star | DECIMAL | 2-star percentage |
| pct_1star | DECIMAL | 1-star percentage |
| pct_extreme_ratings | DECIMAL | % rated 1 or 5 |
| pct_5star_among_unverified | DECIMAL | 5-star rate — unverified reviewers |
| pct_5star_among_verified | DECIMAL | 5-star rate — verified reviewers |

### gold_product_clusters
**Rows:** 497,415 | **Grain:** One row per product | **Tool Mode:** Competitive Positioning, Health Check

| Column | Type | Description |
|--------|------|-------------|
| asin | VARCHAR | Product ASIN |
| subcategory | VARCHAR | Subcategory |
| cluster | INTEGER | Cluster ID (0-4) |
| cluster_name | VARCHAR | Archetype name |
| price_rank | DECIMAL | PERCENT_RANK by price within subcategory |
| sales_rank | DECIMAL | PERCENT_RANK by sales within subcategory |
| reviews_rank | DECIMAL | PERCENT_RANK by reviews within subcategory |

**Cluster archetypes:**
- **Silent Volume Movers** (28.9%): High sales, near-zero reviews
- **Struggling Listers** (largest): Low sales, low engagement
- **Review-Rich Veterans** (13.6%): Many reviews, moderate sales
- **Quiet Quality**: Good ratings, low visibility
- **Best Seller Elite** (1.4%): Badge holders, top performers

### gold_product_trust_scores
**Rows:** 292,401 | **Grain:** One row per product (min 5 reviews) | **Tool Mode:** Review Trust Score

| Column | Type | Description |
|--------|------|-------------|
| parent_asin | VARCHAR | Product ASIN |
| source_category | VARCHAR | Category |
| review_count | INTEGER | Total reviews |
| trust_score | DECIMAL | Isolation Forest anomaly score (lower = more suspicious) |
| reviews_per_day | DECIMAL | Daily review velocity |
| verified_rate | DECIMAL | Verified purchase rate (0-1) |
| pct_5star | DECIMAL | 5-star percentage |
| short_text_rate | DECIMAL | Short review text rate (0-1) |
| reviews_per_reviewer | DECIMAL | Avg reviews per unique reviewer |
| unverified_5star_gap | DECIMAL | Unverified − verified 5-star rate |
| is_suspicious | BOOLEAN | Flagged by Isolation Forest (top 5% anomalous) |

---

## ML Model Artifacts

| File | Model | Purpose |
|------|-------|---------|
| `models/competitive_clusters.pkl` | K-Means (k=5) | Product archetype assignment |
| `models/success_factors.pkl` | XGBoost + SHAP values | Success prediction and feature importance |
| `models/success_model.json` | XGBoost (native format) | Serialized model for inference |
| `models/review_anomaly.pkl` | Isolation Forest | Review manipulation detection |
