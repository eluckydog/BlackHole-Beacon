"""Compare v8.0 vs. Phase 3 rankings"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V8 = os.path.join(ROOT, "data", "classifier_ranking_v8.json")
PHASE3 = os.path.join(ROOT, "data", "phase3_candidates_full.json")

with open(V8) as f:
    v8 = json.load(f)  # list of dicts
with open(PHASE3) as f:
    p3 = json.load(f)  # list of dicts

# Build TOP 50/100 sets
v8_top50 = set(r["designation"] for r in v8[:50])
v8_top100 = set(r["designation"] for r in v8[:100])

p3_sorted = sorted(p3, key=lambda x: x.get("score_total", 0), reverse=True)
p3_top50 = set(c["designation"] for c in p3_sorted[:50])
p3_top100 = set(c["designation"] for c in p3_sorted[:100])

print("BlackHole Beacon - Ranking Comparison (v8.0 vs. Phase 3)")
print("="*80)

print(f"\n--- TOP 50 Overlap ---")
print(f"  v8.0 TOP 50: {len(v8_top50)}")
print(f"  Phase 3 TOP 50: {len(p3_top50)}")
print(f"  Overlap: {len(v8_top50 & p3_top50)} ({100*len(v8_top50 & p3_top50)/50:.1f}%)")

print(f"\n--- TOP 100 Overlap ---")
print(f"  v8.0 TOP 100: {len(v8_top100)}")
print(f"  Phase 3 TOP 100: {len(p3_top100)}")
print(f"  Overlap: {len(v8_top100 & p3_top100)} ({100*len(v8_top100 & p3_top100)/100:.1f}%)")

print(f"\n--- TOP 20 v8.0 vs. Phase 3 ---")
print(f"  {'Rank':<6} {'v8.0 (Isolation Forest)':<30} {'Phase 3 (Score)':<30}")
print(f"  {'-'*6} {'-'*30} {'-'*30}")
for i in range(20):
    v8_name = v8[i]["designation"]
    v8_score = v8[i]["anomaly_score"]
    # Find Phase 3 rank for this source
    p3_rank = None
    p3_score = None
    for j, c in enumerate(p3_sorted):
        if c["designation"] == v8_name:
            p3_rank = j+1
            p3_score = c.get("score_total", 0)
            break
    p3_str = f"Rank {p3_rank} (score={p3_score})" if p3_rank else "N/A"
    print(f"  {i+1:<6} {v8_name:<30} {p3_str:<30}")

print(f"\n--- Diagnosis ---")
print(f"  v8.0 features: IR colors + PM + variability + compactness (9 features)")
print(f"  Phase 3 features: combined score (color + PM + variability + compactness)")
print(f"  Hypothesis:")
print(f"    - v8.0 ranks sources with HIGH anomaly scores (Isolation Forest)")
print(f"    - Phase 3 ranks sources with HIGH combined scores")
print(f"    - Low overlap indicates DIFFERENT candidate preferences.")

print(f"\n{'='*80}")
print(f"CONCLUSION:")
print(f"  v8.0 and Phase 3 rankings are DIFFERENT (overlap {100*len(v8_top50 & p3_top50)/50:.1f}% in TOP 50).")
print(f"  This is EXPECTED because:")
print(f"    1. v8.0 is unsupervised (Isolation Forest)")
print(f"    2. Phase 3 is rule-based (weighted sum of scores)")
print(f"  Next step: Validate v8.0 on known pulsars/black holes.")
print(f"{'='*80}")
