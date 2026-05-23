"""
Compare v7.0 (Isolation Forest) vs. Phase 3 rankings.
WHY are they different?
"""

import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
PLOT_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

print("BlackHole Beacon - Ranking Comparison (v7.0 vs. Phase 3)")
print("="*80)

# ==========
# 1. Load data
# ==========
print("\n--- 1. Load Data ---")

# v7.0 ranking
v7_file = os.path.join(DATA_DIR, "classifier_ranking_v7.json")
with open(v7_file, "r") as f:
    v7_ranking = json.load(f)

# Phase 3 candidates
phase3_file = os.path.join(DATA_DIR, "phase3_candidates_full.json")
with open(phase3_file, "r") as f:
    phase3_candidates = json.load(f)

# Build Phase 3 ranking (by score_total)
phase3_ranking = sorted(
    phase3_candidates,
    key=lambda x: x.get("scores", {}).get("total", 0.0),
    reverse=True
)

print(f"  v7.0 candidates: {len(v7_ranking)}")
print(f"  Phase 3 candidates: {len(phase3_ranking)}")

# ==========
# 2. Compare TOP 20
# ==========
print("\n--- 2. Compare TOP 20 ---")
print("\n  Rank   v7.0 (Isolation Forest)   Phase 3 (Score)")

for i in range(20):
    v7 = v7_ranking[i]
    p3 = phase3_ranking[i]

    v7_anchor = v7["anchor"]
    v7_score = v7["anomaly_score"]
    v7_prob = v7["prob"]

    p3_anchor = p3.get("anchor", "UNK")
    p3_score = p3.get("scores", {}).get("total", 0.0)
    p3_pm = p3.get("proper_motion_masyr", 0.0) or 0.0

    print(f"  {i+1:2d}. {v7_anchor:15s} (prob={v7_prob:.4f})   {p3_anchor:15s} (score={p3_score:.1f}, pm={p3_pm:.1f})")

# ==========
# 3. Overlap analysis
# ==========
print("\n--- 3. Overlap Analysis ---")

v7_top50 = set(r["anchor"] for r in v7_ranking[:50])
p3_top50 = set(c.get("anchor", "UNK") for c in phase3_ranking[:50])

overlap_50 = v7_top50 & p3_top50
print(f"  TOP 50 overlap: {len(overlap_50)} ({len(overlap_50)/50*100:.1f}%)")

v7_top100 = set(r["anchor"] for r in v7_ranking[:100])
p3_top100 = set(c.get("anchor", "UNK") for c in phase3_ranking[:100])

overlap_100 = v7_top100 & p3_top100
print(f"  TOP 100 overlap: {len(overlap_100)} ({len(overlap_100)/100*100:.1f}%)")

# ==========
# 4. Feature analysis (why different?)
# ==========
print("\n--- 4. Feature Analysis (Why Different?) ---")

# v7.0 uses IR colors (J-H, H-K, W1-W2, W2-W3)
# Phase 3 uses combined score (color + PM + variability + compactness)

print("  v7.0 features: IR colors ONLY (J-H, H-K, W1-W2, W2-W3)")
print("  Phase 3 features: combined (color + PM + variability + compactness)")

print("\n  Hypothesis:")
print("    - v7.0 ranks HIGH IR variability sources (pulsar/BH-like colors)")
print("    - Phase 3 ranks HIGH PM + color outliers (more weight on PM)")

# ==========
# 5. Visualization
# ==========
print("\n--- 5. Visualization ---")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle("BlackHole Beacon - Ranking Comparison (v7.0 vs. Phase 3)", fontsize=16)

# 1. TOP 20 overlap (bar chart)
ax = axes[0, 0]
overlap_50_count = len(overlap_50)
overlap_100_count = len(overlap_100)

ax.bar(['TOP 50', 'TOP 100'], [overlap_50_count, overlap_100_count], color=['red', 'blue'])
ax.set_ylabel('Overlap Count')
ax.set_title('TOP 50/100 Overlap (v7.0 vs. Phase 3)')
ax.axhline(y=25, color='gray', linestyle='--', alpha=0.5, label='50% expected')
ax.legend()

# 2. Anomaly score vs. Phase 3 score
ax = axes[0, 1]
v7_probs = [r["prob"] for r in v7_ranking[:100]]
p3_scores = [c.get("scores", {}).get("total", 0.0) for c in phase3_ranking[:100]]

ax.scatter(p3_scores, v7_probs, alpha=0.5, s=10)
ax.set_xlabel("Phase 3 Score")
ax.set_ylabel("v7.0 Anomaly Probability")
ax.set_title("Anomaly Probability vs. Phase 3 Score")

# 3. PM distribution (v7.0 TOP 100 vs. Phase 3 TOP 100)
ax = axes[0, 2]
v7_pms = [r["pm_total"] for r in v7_ranking[:100]]
p3_pms = [c.get("proper_motion_masyr", 0.0) or 0.0 for c in phase3_ranking[:100]]

ax.hist(v7_pms, bins=30, alpha=0.5, label="v7.0 TOP 100", color='red')
ax.hist(p3_pms, bins=30, alpha=0.5, label="Phase 3 TOP 100", color='blue')
ax.set_xlabel("Proper Motion (mas/yr)")
ax.set_ylabel("Count")
ax.set_title("PM Distribution (TOP 100)")
ax.legend()

# 4. IR color distribution (W1-W2)
ax = axes[1, 0]
v7_w1w2 = []
p3_w1w2 = []

for r in v7_ranking[:100]:
    anchor = r["anchor"]
    # Find candidate in phase3_candidates
    for c in phase3_candidates:
        if c.get("anchor", "") == anchor:
            w1 = c.get("W1", None)
            w2 = c.get("W2", None)
            if w1 is not None and w2 is not None:
                v7_w1w2.append(w1 - w2)
            break

for c in phase3_ranking[:100]:
    w1 = c.get("W1", None)
    w2 = c.get("W2", None)
    if w1 is not None and w2 is not None:
        p3_w1w2.append(w1 - w2)

ax.hist(v7_w1w2, bins=30, alpha=0.5, label="v7.0 TOP 100", color='red')
ax.hist(p3_w1w2, bins=30, alpha=0.5, label="Phase 3 TOP 100", color='blue')
ax.set_xlabel("W1-W2 (WISE)")
ax.set_ylabel("Count")
ax.set_title("W1-W2 Distribution (TOP 100)")
ax.legend()

# 5. Score difference (v7.0 - Phase 3)
ax = axes[1, 1]
# Build mapping: anchor -> rank (v7.0 and Phase 3)
v7_rank = {r["anchor"]: i+1 for i, r in enumerate(v7_ranking)}
p3_rank = {c.get("anchor", "UNK"): i+1 for i, c in enumerate(phase3_ranking)}

rank_diffs = []
for anchor in v7_top100:
    if anchor in p3_rank:
        diff = v7_rank[anchor] - p3_rank[anchor]
        rank_diffs.append(diff)

ax.hist(rank_diffs, bins=30, alpha=0.7, color='purple')
ax.set_xlabel("Rank Difference (v7 - Phase 3)")
ax.set_ylabel("Count")
ax.set_title("Rank Difference Distribution")
ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)

# 6. Summary table
ax = axes[1, 2]
ax.axis('off')
summary_text = f"""
Summary:
-------
v7.0 TOP 1: {v7_ranking[0]['anchor']}
  (prob={v7_ranking[0]['prob']:.4f})

Phase 3 TOP 1: {phase3_ranking[0].get('anchor', 'UNK')}
  (score={phase3_ranking[0].get('scores', {}).get('total', 0.0):.1f})

TOP 50 overlap: {len(overlap_50)} ({len(overlap_50)/50*100:.1f}%)
TOP 100 overlap: {len(overlap_100)} ({len(overlap_100)/100*100:.1f}%)

Key Difference:
- v7.0: IR colors ONLY
- Phase 3: color + PM + variability
"""
ax.text(0.1, 0.5, summary_text, fontsize=10, family='monospace')

plt.tight_layout()
plot_file = os.path.join(PLOT_DIR, "ranking_comparison_v7_vs_phase3.png")
plt.savefig(plot_file, dpi=150)
plt.close()

print(f"  Saved: {plot_file}")

# ==========
# 6. Save comparison results
# ==========
print("\n--- 6. Save Comparison Results ---")

comparison = {
    "v7_top1": v7_ranking[0]["anchor"],
    "v7_top1_prob": v7_ranking[0]["prob"],
    "phase3_top1": phase3_ranking[0].get("anchor", "UNK"),
    "phase3_top1_score": phase3_ranking[0].get("scores", {}).get("total", 0.0),
    "top50_overlap": len(overlap_50),
    "top50_overlap_pct": len(overlap_50)/50*100,
    "top100_overlap": len(overlap_100),
    "top100_overlap_pct": len(overlap_100)/100*100,
    "v7_top20": [r["anchor"] for r in v7_ranking[:20]],
    "phase3_top20": [c.get("anchor", "UNK") for c in phase3_ranking[:20]]
}

comparison_file = os.path.join(DATA_DIR, "ranking_comparison_v7_vs_phase3.json")
with open(comparison_file, "w") as f:
    json.dump(comparison, f, indent=2)

print(f"  Saved: {comparison_file}")

# ==========
# 7. Conclusion
# ==========
print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

print(f""" 
  v7.0 and Phase 3 rankings are DIFFERENT because:
  
  1. v7.0 uses ONLY IR colors (J-H, H-K, W1-W2, W2-W3)
     -> Ranks sources with pulsar/BH-like IR spectra
     
  2. Phase 3 uses combined score (color + PM + variability + compactness)
     -> Ranks sources with HIGH PM + color outliers
  
  TOP 50 overlap: {len(overlap_50)} ({len(overlap_50)/50*100:.1f}%)
  -> Indicates DIFFERENT candidate preferences.
  
  NEXT STEP:
  - Validate v7.0 on known pulsars/black holes
  - If v7.0 TOP 50 contains known sources -> v7.0 is effective
  - If not -> adjust Isolation Forest parameters (contamination)
""")

print("="*80)
print("DONE. Comparison complete.")
print("="*80)
