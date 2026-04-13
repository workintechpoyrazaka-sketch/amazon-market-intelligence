# Amazon Market Intelligence

**What actually drives product success on Amazon — and can we turn that knowledge into a tool that helps sellers make better decisions?**

I took 37 GB of raw Amazon product data and 526M customer reviews, built a full intelligence pipeline, discovered what actually drives success on the world's biggest marketplace, and turned it into a tool that any seller can use to make better decisions.

---

## The Problem

Amazon sellers make pricing, positioning, and category decisions blindly. "Cheap wins" is conventional wisdom. "More reviews = more sales" is assumed. "Just get the Best Seller badge" is the dream. **None of it holds up across all categories.**

## The Data

| Source | What | Scale |
|--------|------|-------|
| Kaggle Amazon Products | Products with prices, ratings, sales, Best Seller flags | 1.4M products |
| Kaggle Amazon Categories | Category taxonomy | 248 subcategories |
| McAuley Lab Metadata | Products with stores, brands, features, descriptions | 35M products |
| McAuley Lab Reviews | Review text, ratings, timestamps, user IDs | 526M reviews |

**Total raw data: ~200+ GB across 4 sources.**

---

## Key Findings

### 📍 Category Landscape — Where the Money Is

Not all categories are created equal. Kitchen & Dining alone generates **$267M** — more than the bottom 100 combined. But raw revenue is misleading; **revenue per product** reveals where demand actually concentrates.

![Top 20 Subcategories by Revenue](notebooks/charts/03_category_landscape/01_top20_revenue.png)

![Revenue per Product — Demand Density](notebooks/charts/03_category_landscape/02_revenue_per_product.png)

The **Opportunity Quadrant** plots every subcategory by demand density vs. activity rate. Bubble size = competition. Top-right, small bubble = the sweet spot.

![Opportunity Quadrant](notebooks/charts/03_category_landscape/03_opportunity_quadrant.png)

Every subcategory classified into four strategic types — Stars, Niche Premium, Volume Plays, and Graveyards:

![Category Typology](notebooks/charts/03_category_landscape/13_category_typology.png)

Ratings are declining industry-wide (4.28 → 4.02, 2019–2022), and growth varies wildly by category:

![Growers vs Decliners](notebooks/charts/03_category_landscape/10_growers_vs_decliners.png)

![Growth Heatmap](notebooks/charts/03_category_landscape/09_growth_heatmap.png)

---

### 💰 Pricing & Discounts — "Cheap Wins" Is Dead

Budget wins only **6 of 248** subcategories. Low-price products capture the most total revenue, but Luxury earns **$6,624 per product** — 19× more than Budget. The winning price tier is entirely category-dependent.

![Revenue by Price Tier](notebooks/charts/04_pricing_discounts/01_revenue_by_tier.png)

![Luxury vs Budget](notebooks/charts/04_pricing_discounts/04_luxury_vs_budget.png)

![Revenue Share by Tier — Top 15 Categories](notebooks/charts/04_pricing_discounts/03_revenue_share_by_tier.png)

No-discount products earn the most per listing ($7,903), but **Light discounts (1–19%)** dominate 144 categories. Deep discounts (50%+) win only 4. The discount sweet spot is lighter than most sellers think.

![Revenue by Discount Band](notebooks/charts/04_pricing_discounts/06_revenue_by_discount.png)

![Discount Curve](notebooks/charts/04_pricing_discounts/07_discount_curve.png)

---

### 🏷️ Brand & Listing Quality — Branding Is a Niche Weapon

Unbranded products dominate total revenue ($3.6B vs $1B), but branded earns slightly more per product ($3,634 vs $3,171). The brand multiplier ranges from **206× (Sony PSP)** to near-zero — it's entirely category-dependent.

![Branded vs Unbranded](notebooks/charts/05_brand_listing_quality/01_branded_vs_unbranded_overall.png)

![Brand Multiplier by Category](notebooks/charts/05_brand_listing_quality/02_brand_multiplier.png)

![Brand Penetration](notebooks/charts/05_brand_listing_quality/03_brand_presence.png)

Listing completeness (features, descriptions, brand, store info) has a **median multiplier below 1.0×** — meaning it doesn't help in the typical category. But in specific categories, complete listings earn up to **27× more**. The Best Seller badge is rare (median 0.3% of products) but can mean **997× revenue** in niche categories like Wii Games.

![Listing Element Impact](notebooks/charts/05_brand_listing_quality/04_listing_element_multipliers.png)

![Best Seller Multiplier](notebooks/charts/05_brand_listing_quality/08_bestseller_multiplier.png)

![Success Signal Correlation Matrix](notebooks/charts/05_brand_listing_quality/10_success_correlation_matrix.png)

---

### 🏪 Store & Seller Patterns — Focus Beats Breadth

54% of Amazon stores sell exactly one product. The seller economy is a long tail — **top 1.2% of stores hold 50% of all revenue**. Store type matters: Specialists ($4,172/product) and Focused sellers ($4,066) outperform Generalists ($2,903) by 44%. But Generalists dominate total revenue ($878M) through sheer volume.

![Store Size Distribution](notebooks/charts/06_store_seller_patterns/01_store_size_distribution.png)

![Size Tier — Stores vs Revenue](notebooks/charts/06_store_seller_patterns/02_size_tier_split.png)

![Specialist vs Generalist](notebooks/charts/06_store_seller_patterns/03_specialist_vs_generalist.png)

Adding categories doesn't help — per-product revenue declines as stores diversify. And store ratings have near-zero correlation with revenue (0.036).

![Category Count vs Revenue](notebooks/charts/06_store_seller_patterns/04_category_count_vs_revenue.png)

![Revenue Concentration Curve](notebooks/charts/06_store_seller_patterns/06_revenue_concentration.png)

---

### 💬 Reviews & Sentiment — What 526M Reviews Actually Say

Subscription Boxes (25.1% negative) and All Beauty (20.7%) are the most complained-about categories. Digital content (Kindle, CDs, Digital Music) has the happiest customers at 6–7% negative. Across all categories, unhappy customers write **1.33× longer** reviews — with Gift Cards hitting 2.98×.

![Negative Rate by Category](notebooks/charts/07_reviews_sentiment/01_negative_rate_by_category.png)

![Verbosity Ratio](notebooks/charts/07_reviews_sentiment/03_verbosity_ratio.png)

Generic word frequency is misleading. Using **complaint-distinctive ratios** (negative ÷ positive usage), the real complaint signals emerge: "inedible" (699×), "rancid" (396×), "unsafe" (226×). Praise signals are dominated by book reviews — "captivating" (3,851×), "gripping" (2,999×) — and food: "yum" (3,555×).

![Complaint-Distinctive Keywords](notebooks/charts/07_reviews_sentiment/04_distinctive_negative_keywords.png)

![Praise-Distinctive Keywords](notebooks/charts/07_reviews_sentiment/06_distinctive_positive_keywords.png)

![Category Complaint Signatures](notebooks/charts/07_reviews_sentiment/05_complaint_keywords_by_category.png)

89.2% of reviews are verified purchases. The "fake review" narrative doesn't hold: unverified reviewers give **fewer** 5-star ratings than verified ones (−8.6 percentage points on average). The gap is negative across every single category.

![Verified Purchase Rate](notebooks/charts/07_reviews_sentiment/06_verified_rate_by_category.png)

![Unverified vs Verified Gap](notebooks/charts/07_reviews_sentiment/08_verified_unverified_gap.png)

---

### 🎯 Competitive Clustering — Five Archetypes on Amazon

K-Means clustering on category-relative features (percentile ranks within subcategory) reveals five product archetypes. Features are nearly uncorrelated (max 0.13), meaning each captures independent signal.

![Cluster Sizes](notebooks/charts/08_competitive_clustering/05_cluster_sizes.png)

| Cluster | Products | Avg Revenue/Product | Key Trait |
|---------|----------|-------------------|-----------|
| Silent Volume Movers | 143K (28.9%) | $16,554 | High sales, near-zero reviews — selling on demand alone |
| Struggling Listers | 138K (27.7%) | $3,968 | Longest titles, highest prices, worst ratings — effort ≠ quality |
| Review-Rich Veterans | 68K (13.6%) | $11,415 | 2,213 avg reviews but only moderate sales — social proof ≠ dominance |
| Quiet Quality | 141K (28.4%) | $3,535 | Best ratings, shortest titles, low visibility |
| Best Seller Elite | 6.7K (1.4%) | $63,457 | 100% badge holders, 18× more revenue per product than Quiet Quality |

![Cluster Radar Profiles](notebooks/charts/08_competitive_clustering/06_cluster_radar.png)

![Revenue by Cluster](notebooks/charts/08_competitive_clustering/07_revenue_by_cluster.png)

PCA reveals two dimensions explaining the marketplace: **PC1 = success** (sales + badge + reviews), **PC2 = effort vs quality** (title length vs rating). Best Seller Elite separates cleanly on PC1; Struggling Listers spread high on PC2.

![PCA Projection](notebooks/charts/08_competitive_clustering/08_pca_projection.png)

Review-Rich Veterans concentrate in specific categories — Makeup (56%), Home Décor (55%), Automotive Tools (53%) — but are absent from Bath, Bedding, and Hair Care. Review accumulation is category-dependent.

![Cluster × Category Heatmap](notebooks/charts/08_competitive_clustering/09_cluster_subcategory_heatmap.png)

---

### 🔬 Success Factor Discovery — What Actually Predicts Success?

XGBoost + SHAP on 497K active products, predicting top-25% revenue within subcategory. 14 listing-visible features, zero data leakage (sales/revenue excluded from features). Model achieves **AUC 0.78** — listing attributes predict most of success, but ~22% is marketplace randomness.

**The headline: price positioning is the #1 predictor.** SHAP ranks `price_rank` at 0.62 mean |SHAP value| — 3× higher than any other feature. Where you price within your category matters more than badge, reviews, brand, or listing completeness.

![SHAP Summary](notebooks/charts/09_success_factors/05_shap_summary.png)

![SHAP Feature Importance](notebooks/charts/09_success_factors/06_shap_bar.png)

**XGBoost vs SHAP tell different stories.** XGBoost Gain ranks `is_best_seller` #1 (0.36), but SHAP drops it to #11. The badge fires massively (+2.09 SHAP) for the 1.4% who have it, but contributes zero for 98.6% of products. Price_rank affects *every* product.

![Feature Direction](notebooks/charts/09_success_factors/08_feature_direction.png)

**Individual product diagnosis — the tool's power.** SHAP waterfall plots show exactly *why* a product succeeds or struggles. A $1.50 product at the bottom of its category (price_rank = 0) gets −1.19 and −0.88 SHAP from price alone. A 4.6 rating (+0.14) can't save it.

![Waterfall — Success](notebooks/charts/09_success_factors/09a_waterfall_success.png)

![Waterfall — Struggle](notebooks/charts/09_success_factors/09b_waterfall_struggle.png)

Price_rank success rate climbs from 10% (bottom quintile) to 52% (top quintile) — a 5× improvement. Rating shows a cliff below 4.0 but is flat above it. Any discount helps; the size barely matters.

![Success Rate by Feature](notebooks/charts/09_success_factors/10_success_rate_by_feature.png)

---

### 🛡️ Review Anomaly Detection — Can You Trust These Reviews?

Isolation Forest (unsupervised) on 292K products with 5+ reviews, flagging the 5% with most unusual review patterns. No labeled "fake" data exists, so anomaly detection finds statistical outliers — products whose review patterns deviate from the population.

**14,620 products flagged as suspicious (5%).** The typical product scores 87.3 trust (median), confirming Amazon's review ecosystem is overwhelmingly authentic — but the 5% tail reveals real manipulation patterns.

What makes a product suspicious: **54.5% verified rate** (vs 93.5% normal), **6.7× higher review velocity**, and critically — a **positive unverified 5-star gap** (+2.8 vs −8.6 normal). Market-wide, unverified reviews are *less* generous. On suspicious products, the pattern reverses. That's what targeted manipulation looks like.

![Trust Score Distribution](notebooks/charts/10_review_anomaly/02_trust_score_distribution.png)

![Anomaly vs Normal](notebooks/charts/10_review_anomaly/03_anomaly_vs_normal.png)

![Anomaly Rate by Category](notebooks/charts/10_review_anomaly/05_anomaly_rate_by_category.png)

![Suspicious Deviations](notebooks/charts/10_review_anomaly/08_suspicious_deviations.png)

---

## Validated Insights (So Far)

- **"Cheap wins" is false** — Luxury earns 19× more per product than Budget; Budget wins only 6 of 248 subcategories
- **Light discounts beat deep discounts** — Light (1–19%) dominates 144 categories; Deep (50%+) wins only 4
- **No-discount products earn the most per listing** — $7,903 vs $3,600 for Light discounts
- **Brand advantage is category-dependent** — ranges from 206× (Sony PSP) to near-zero
- **Unbranded dominates total revenue** — $3.6B vs $1B, but branded earns 14% more per product
- **Listing completeness matters in specific categories, not universally** — median multiplier <1×, but max 27×
- **Best Seller badge is rare and category-dependent** — median 0.3%, multiplier from 997× (Wii Games) to negligible
- **Specialization beats diversification** — Specialists earn 44% more per product than Generalists
- **Store economy is winner-take-most** — top 1.2% of stores hold 50% of revenue
- **Store ratings don't predict revenue** — correlation 0.036
- **Ratings are declining industry-wide** (4.28 → 4.02, 2019–2022)
- **Unverified reviews are LESS positive than verified** — −8.6pp gap kills the fake review inflation narrative
- **Complaint keywords are category-specific** — "inedible" and "rancid" (food), "unsafe" (electronics), "shoddy" (goods)
- **Negative reviews are 1.33× longer than positive** — unhappy customers write more, providing richer signal
- **89.2% of reviews are verified purchases** — Amazon's review base is overwhelmingly authentic
- **Five competitive archetypes exist across all categories** — Silent Volume Movers, Struggling Listers, Review-Rich Veterans, Quiet Quality, Best Seller Elite
- **Best Seller Elite (1.4% of products) earns 18× more per product** — $63.5K vs $3.5K for Quiet Quality
- **Keyword-stuffed titles correlate with worst ratings** — Struggling Listers have longest titles but lowest ratings (4.28)
- **You don't need reviews to sell** — Silent Volume Movers average 774 monthly sales with near-zero reviews
- **Review accumulation is category-dependent** — Veterans concentrate in Makeup (56%), Home Décor (55%), absent from Bath/Bedding
- **Price positioning is the #1 success predictor** — SHAP value 0.62, 3× higher than any other feature
- **Listing features predict 78% of success variance (AUC 0.78)** — meaningful but ~22% is marketplace randomness
- **Best Seller badge: decisive for 1.4%, irrelevant for 98.6%** — XGBoost Gain #1 but SHAP #11
- **Premium pricing within category = 5× higher success rate** — bottom quintile 10%, top quintile 52%
- **Rating cliff at 4.0** — getting above 4.0 matters; incremental gains from 4.0→5.0 don't predict success
- **Any discount helps, size doesn't matter** — binary SHAP jump at non-zero discount, flat after that
- **has_description slightly hurts success prediction** — counterintuitive; may reflect data coverage patterns
- **5% of products have suspicious review patterns** — 14,620 of 292K flagged by Isolation Forest
- **Verified rate is the #1 anomaly signal** — suspicious products average 54.5% verified vs 93.5% normal
- **Unverified 5-star gap reverses on suspicious products** — +2.8 vs −8.6 normal; targeted manipulation flips the market-wide pattern
- **Suspicious reviews are LONGER, not shorter** — 413 chars vs 172; organized campaigns write full-length text
- **Review velocity 6.7× higher on suspicious products** — burst patterns are the second strongest signal

---

## Architecture

```
Bronze → Silver → Gold → Notebooks → ML → Streamlit App
```

- **Bronze (4 tables):** Raw ingestion — 1.4M products, 35M metadata, 248 categories, 526M reviews
- **Silver (5 tables/views):** Cleaned, typed, enriched — quality flags, joins, deduplication
- **Gold (18 tables):** Pre-aggregated analytics — one table per analytical question, plus ML outputs
- **Engine:** DuckDB (local, no cloud dependency, handles 200+ GB)
- **Stack:** Python · DuckDB · Pandas · Plotly · scikit-learn · XGBoost · VADER · Streamlit

## The Tool (In Progress)

**5 modes, 11 customer questions:**

| Mode | Questions It Answers |
|------|---------------------|
| 🔍 Category Scout | Where should I sell? Is my category growing? How competitive is it? |
| 📊 Competitive Positioning | What's the price sweet spot? Who are my competitors? |
| 🏥 Health Check | How does my product compare? What am I doing wrong? |
| 💬 Voice of Customer | What are customers actually saying? |
| 🛡️ Review Trust Score | Can I trust these reviews? |

---

## Project Structure

```
amazon-market-intelligence/
├── collection/           # Raw data files (not in repo)
├── pipeline/             # Bronze → Silver → Gold scripts
│   ├── bronze_*.py       # 4 Bronze ingestion scripts
│   ├── silver_*.py       # 5 Silver transform scripts
│   └── gold_*.py         # 11 Gold aggregation scripts
├── notebooks/            # Analysis & ML notebooks
│   ├── 01_eda_kaggle.ipynb
│   ├── 02_eda_mcauley_metadata.ipynb
│   ├── 03_category_landscape.ipynb
│   ├── 04_pricing_discounts.ipynb
│   ├── 05_brand_listing_quality.ipynb
│   ├── 06_store_seller_patterns.ipynb
│   ├── 07_reviews_sentiment.ipynb
│   ├── 08_competitive_clustering.py
│   ├── 09_success_factors.py
│   ├── 10_review_anomaly.py
│   └── charts/           # Generated visualizations
├── models/               # Trained ML models
├── app/                  # Streamlit application
└── data/                 # DuckDB database (not in repo)
```

## What's Next

- [x] Category Landscape Analysis
- [x] Pricing & Discount Analysis
- [x] Brand & Listing Quality Analysis
- [x] Store & Seller Patterns
- [x] Review & Sentiment Analysis
- [x] ML: Competitive Clustering (K-Means — 5 archetypes, 10 charts)
- [x] ML: Success Factor Discovery (XGBoost + SHAP — AUC 0.78, 11 charts)
- [x] ML: Review Anomaly Detection (Isolation Forest — 5% flagged, 10 charts)
- [ ] Streamlit interactive tool
- [ ] Presentation deck

---

*Built by Poi — data professional in transition. This project is part of a 10-month Data Analyst → Data Scientist program.*
