# Findings

100 findings from 8 analysis sessions across 1.4M products, 35M metadata records, and 526M reviews.

---

## The Marketplace is a Ghost Town

Most of Amazon's catalog is dead weight. The active marketplace is a thin layer on top of a massive graveyard.

- **#1:** 77.4% of Kaggle products have zero reviews
- **#2:** 64.3% have zero sales — a "ghost marketplace"
- **#3:** Power law: 0.4% of products generate 25% of revenue, but the mid-tier (6.4%) accounts for 48%
- **#5:** Sales gap at 50 — no values between 1-49; Amazon rounds small values to zero
- **#9:** `boughtInLastMonth` has clean distribution above 50, unreliable below
- **#68:** 54.3% of stores sell exactly one product — the long tail of micro-sellers
- **#72:** Top 1.2% of stores hold 50% of revenue — more concentrated than product-level power law

## Category Dynamics

Revenue and competition vary wildly across categories. There is no universal Amazon strategy.

- **#4:** Kitchen & Dining dominates at 10.4M units from 4,900 products — highest demand-per-product ratio
- **#19:** Kitchen & Dining leads revenue at $267M with 99.1% active products
- **#20:** Hair Care 99.7% active — virtually zero dead inventory
- **#28:** 73% of Kaggle products have NULL `main_category` — only 381K of 1.4M match McAuley
- **#57:** No single price tier universally wins: Low dominates 111 subcategories, Mid 59, Luxury 55, Premium 17

## "Cheap Wins" is Dead

One of the project's strongest findings: the race to the bottom doesn't work on Amazon.

- **#21:** Luxury products earn $283K/product vs Budget $15K (18×) in Kitchen & Dining
- **#22:** Mid-tier leads total revenue ($87M) in Kitchen — the price sweet spot is mid-range
- **#54:** Low price tier wins total revenue ($1.5B, 32.5%) — volume play
- **#55:** But Luxury earns $6,624/product — 19× more per listing than Budget
- **#56:** Budget tier wins only 6 of 248 subcategories
- **#89:** SHAP ranks price positioning within category as #1 success predictor (0.62 mean |SHAP|, 3× any other feature)
- **#93:** Price rank success rate: 10% (bottom quintile) → 52% (top quintile) — 5× improvement

## Brand Advantage is Category-Dependent

Brand matters enormously in some categories and not at all in others.

- **#11:** Brand is 62% NULL overall — much higher than Electronics alone (28%)
- **#26:** Brand multiplier ranges from 207× (Sony PSP) to ~1×
- **#61:** Unbranded dominates total revenue: $3.6B vs $1B branded
- **#62:** Branded earns $3,634/product vs Unbranded $3,171 (14% more) — modest overall premium
- **#63:** Confirmed at full scale: brand value is entirely category-dependent
- **#65:** Brand has strongest revenue correlation (+0.200) among listing elements

## Discounts: Less is More

Deep discounting is almost never the answer.

- **#58:** No-discount products earn $7,903/product — highest per-listing value
- **#59:** Light discounts (1-19%) dominate 144 categories
- **#60:** Deep discounts (50%+) win only 4 of 248 categories
- **#95:** SHAP shows a binary jump — having any discount listed helps, but magnitude barely matters

## Listing Quality Surprises

Conventional listing optimization wisdom doesn't hold at scale.

- **#64:** Listing element multipliers all ≤1.0× at median — completeness doesn't reliably help
- **#86:** Struggling Listers have the longest titles (0.74 rank) but worst ratings (4.28) — keyword stuffing correlates with lower quality
- **#92:** `has_description` has negative SHAP direction — counterintuitive, may reflect data coverage patterns

## Best Seller Badge

The badge creates astronomical advantages for the tiny minority who have it.

- **#6:** 1,738 Best Seller products have zero sales — badge doesn't guarantee current performance
- **#66:** Median badge rate 0.3%, only 8 categories exceed 5% — extremely rare
- **#67:** Best Seller multiplier: Wii Games 997×, but varies enormously by category
- **#85:** Best Seller Elite cluster (1.4%) earns $63.5K/product — 18× more than Quiet Quality
- **#91:** XGBoost Gain ranks `is_best_seller` #1 (0.36) but SHAP ranks it #11 — fires hugely for 1.4%, zero for 98.6%

## Store & Seller Patterns

Specialization beats diversification, but generalists dominate total volume.

- **#23:** 4.77M stores, 91% are Specialists (single category)
- **#24:** Specialists earn $4,172/product vs Generalists $2,903 (44% more)
- **#25:** Generalists overrepresented in Kaggle-matched data (40K of 92K)
- **#69:** Three store types, not binary: Specialist (23.1%), Focused (33.4%), Generalist (43.5%)
- **#70:** Specialist $4,172 > Focused $4,066 > Generalist $2,903 per product — focus wins but Specialist-Focused gap is tiny
- **#71:** Generalists dominate total revenue: $878M (66%) — volume × products overcomes lower efficiency
- **#73:** Rating-revenue correlation: 0.036 — rating is essentially irrelevant to store-level revenue

## Reviews: What They Tell Us

Reviews follow the same power law as everything else. Negative reviewers write more and get more helpful votes.

- **#8:** 77% of ratings are 4.0-5.0 — rating inflation is real
- **#27:** Reviews p75 = 0 in Kitchen, but median sales = 1,000 — products sell without reviews
- **#79:** Median 12 reviews/product, mean 69 — extreme skew
- **#84:** Silent Volume Movers (28.9%) dominate revenue at $2.4B with 774 avg sales and near-zero reviews — you don't need reviews to sell
- **#88:** Review-Rich Veterans (13.6%) have 2,213 avg reviews but only moderate sales — social proof alone doesn't sustain sales
- **#94:** Rating SHAP cliff below 4.0, flat 4.0-5.0 — getting above 4.0 matters; incremental gains above don't

## Sentiment & Keywords

What customers actually complain about, and what they praise.

- **#74:** Subscription Boxes 25.1% negative, All_Beauty 20.7% — worst customer satisfaction
- **#75:** Kindle/CDs/Digital Music lowest negativity (6-7%) — digital content has happiest customers
- **#80:** Complaint-distinctive words: "inedible" (699×), "rancid" (396×), "unsafe" (226×)
- **#81:** Praise-distinctive words dominated by books + food: "captivating" (3,851×), "gripping" (2,999×), "yum" (3,555×)
- **#82:** "Excelente" at 67K uses in praise keywords — large Spanish-speaking reviewer base

## Review Trust & Fake Detection

Amazon reviews are overwhelmingly legitimate — but the 5% that aren't show a distinctive, detectable pattern.

- **#76:** 89.2% overall verified purchase rate
- **#77:** CDs & Vinyl only 67.9% verified — lowest category
- **#78:** Unverified 5-star gap: −8.6 percentage points average — unverified reviewers are LESS generous than verified buyers
- **#96:** 5% of products flagged as suspicious (14,620 of 292K)
- **#97:** Verified rate is the top anomaly signal: 54.5% suspicious vs 93.5% normal
- **#98:** Suspicious products have a positive unverified 5-star gap (+2.8) vs normal (−8.6) — the market-wide pattern reverses on exactly these products
- **#99:** Review velocity 6.7× higher for suspicious products (0.37/day vs 0.05) — burst patterns are the second strongest signal
- **#100:** Suspicious reviews are LONGER (413 chars vs 172) — organized campaigns write full text, not short bot spam

## Competitive Archetypes

K-Means reveals 5 distinct competitive profiles that any seller can identify with.

- **#83:** k=5 optimal — silhouette flat (0.18-0.22), business interpretability chose k, not math
- **#84:** Silent Volume Movers (28.9%): $2.4B revenue, 774 avg sales, near-zero reviews
- **#85:** Best Seller Elite (1.4%): $63.5K/product — 18× more than Quiet Quality
- **#86:** Struggling Listers: longest titles, worst ratings — effort without quality
- **#87:** PCA: PC1 = success axis (sales + badge + reviews), PC2 = effort vs quality
- **#88:** Review-Rich Veterans (13.6%): 2,213 avg reviews, moderate sales — social proof ≠ revenue

## ML Model Performance

Listing-visible features predict most of success. The rest is marketplace randomness.

- **#89:** SHAP: price_rank #1 at 0.62, 3× higher than any other feature
- **#90:** XGBoost AUC 0.78 — 78% of success variance explained by listing-visible features
- **#91:** XGBoost Gain vs SHAP disagreement on `is_best_seller` — a lesson in interpretation
- **#93:** Price rank: 10% → 52% success rate across quintiles
- **#94:** Rating cliff at 4.0 — threshold effect, not linear
- **#95:** Discount: binary signal (any discount helps), magnitude secondary

## Data Engineering Findings

Discoveries about the data itself that shaped pipeline design.

- **#7:** 97 duplicate ASINs in Kaggle — minor, flagged not removed
- **#10:** McAuley: 35M rows, 33 categories, 7 core fields
- **#12:** 50 distinct `main_category` values in 33 CSV files — cross-category tagging
- **#13:** Em-dash "—" used as null for price in McAuley
- **#14:** Health_and_Personal_Care (60K) vs Health_and_Household (798K) — possible overlap
- **#15:** ASIN join is 1:1 clean — zero duplicates
- **#16:** 28.5% match rate (406K of 1.4M)
- **#17:** 2.3M NULL categories in McAuley (7%)
- **#18:** 35M-row CREATE TABLE takes 15+ min — VIEW pattern discovered
- **#50:** gold_review_keywords = 165,858 rows from 10% sample
- **#51:** Clothing categories have ~1% review match rate
- **#52:** Batch-by-category processing prevents thermal issues
- **#53:** APPROX_QUANTILE is viable MEDIAN replacement (99.9% accuracy, 10× speed)
