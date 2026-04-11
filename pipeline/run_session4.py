import subprocess, time, sys

scripts = [
    "pipeline/silver_reviews.py",
    "pipeline/gold_discount_effectiveness.py",
    "pipeline/gold_listing_quality.py",
    "pipeline/gold_bestseller_analysis.py",
    "pipeline/gold_temporal_trends.py",
    "pipeline/gold_review_trust.py",
    "pipeline/gold_review_sentiment.py",
]

total_start = time.time()
for i, script in enumerate(scripts):
    print(f"\n{'='*60}")
    print(f"[{i+1}/{len(scripts)}] Running {script}")
    print('='*60)
    result = subprocess.run([sys.executable, script], cwd="C:/Users/thinkpad/Desktop/amazon-market-intelligence")
    if result.returncode != 0:
        print(f"FAILED at {script} — stopping.")
        break

print(f"\n{'='*60}")
print(f"ALL DONE in {(time.time()-total_start)/60:.1f} minutes")
