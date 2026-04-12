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
- **Unverified reviews are less positive than verified** — the opposite of what you'd expect

---

## Architecture

```
Bronze → Silver → Gold → Notebooks → ML → Streamlit App
```

- **Bronze (4 tables):** Raw ingestion — 1.4M products, 35M metadata, 248 categories, 526M reviews
- **Silver (5 tables/views):** Cleaned, typed, enriched — quality flags, joins, deduplication
- **Gold (16 tables):** Pre-aggregated analytics — one table per analytical question
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
- [ ] Review & Sentiment Analysis (VADER NLP)
- [ ] ML: Competitive Clustering (K-Means)
- [ ] ML: Success Factor Discovery (XGBoost + SHAP)
- [ ] ML: Review Anomaly Detection
- [ ] Streamlit interactive tool
- [ ] Presentation deck

---

*Built by Poi — data professional in transition. This project is part of a 10-month Data Analyst → Data Scientist program.*
