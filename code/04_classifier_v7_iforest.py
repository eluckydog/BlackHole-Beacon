"""
BlackHole Beacon — Anomaly Detection v7.0 (Isolation Forest)

Uses Isolation Forest (UNSUPERVISED) to find outliers in feature space.
NO labeled negative samples needed!
Directly outputs anomaly scores (higher = more likely pulsar/BH).
"""

import json
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
PLOT_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

# ==========
# 1. Load data
# ==========
print("BlackHole Beacon — Anomaly Detection v7.0 (Isolation Forest)")
print("="*80)

print("\n--- 1. Load Data ---")

# Load Phase3 candidates
phase3_file = os.path.join(DATA_DIR, "phase3_candidates_full.json")
with open(phase3_file, "r") as f:
    candidates = json.load(f)

print(f"  Phase 3 candidates (full): {len(candidates)}")

# ==========
# 2. Build feature matrix (ALL candidates, NO labels)
# ==========
print("\n--- 2. Build Feature Matrix (ALL candidates, UNSUPERVISED) ---")

def extract_features(candidate):
    """Extract 9 features (IR colors + PM)."""
    features = []
    
    # 1-4: IR colors
    j = candidate.get("J", None)
    h = candidate.get("H", None)
    k = candidate.get("K", None)
    w1 = candidate.get("W1", None)
    w2 = candidate.get("W2", None)
    w3 = None  # Not available in phase3_candidates_full.json
    
    j_h = (j - h) if (j is not None and h is not None) else 0.0
    h_k = (h - k) if (h is not None and k is not None) else 0.0
    w1_w2 = (w1 - w2) if (w1 is not None and w2 is not None) else 0.0
    w2_w3 = (w2 - w3) if (w2 is not None and w3 is not None) else 0.0
    
    features.extend([j_h, h_k, w1_w2, w2_w3])
    
    # 5-9: Proper motion
    pm_total = candidate.get("proper_motion_masyr", 0.0) or 0.0
    pm_ra = 0.0  # Can't split from total
    pm_dec = 0.0
    abs_pm_ra = 0.0
    abs_pm_dec = 0.0
    
    features.extend([pm_ra, pm_dec, abs_pm_ra, abs_pm_dec, pm_total])
    
    return features

# Build feature matrix for ALL candidates
X = np.array([extract_features(c) for c in candidates])
print(f"  Feature matrix: {X.shape}")
print(f"  Features: 9 (IR colors 1-4, PM 5-9)")

# ==========
# 3. Train Isolation Forest
# ==========
print("\n--- 3. Train Isolation Forest ---")

# Standardize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Isolation Forest
print("  Training Isolation Forest...")
iso_forest = IsolationForest(
    n_estimators=200,
    max_samples='auto',
    contamination=0.1,  # Assume 10% are anomalies (pulsars/BH)
    random_state=42,
    n_jobs=-1
)

iso_forest.fit(X_scaled)
print("  Done!")

# ==========
# 4. Anomaly scores
# ==========
print("\n--- 4. Anomaly Scores ---")

# Decision function (higher = more anomalous)
scores = iso_forest.decision_function(X_scaled)

# Convert to 0-1 range (higher = more likely pulsar/BH)
probs = (scores - scores.min()) / (scores.max() - scores.min())

print(f"  Anomaly score range: [{scores.min():.4f}, {scores.max():.4f}]")
print(f"  Probability range: [{probs.min():.4f}, {probs.max():.4f}]")

# ==========
# 5. Rank all candidates
# ==========
print("\n--- 5. Rank All Candidates ---")

ranking = []
for i, c in enumerate(candidates):
    rank = c.get("rank", i+1)
    anchor = c.get("anchor", f"UNK_{i}")
    designation = c.get("designation", "")
    
    ranking.append({
        "rank": rank,
        "anchor": anchor,
        "designation": designation,
        "anomaly_score": float(scores[i]),
        "prob": float(probs[i]),
        "score_total": c.get("scores", {}).get("total", 0.0),
        "pm_total": c.get("proper_motion_masyr", 0.0) or 0.0
    })

# Sort by anomaly score (descending)
ranking = sorted(ranking, key=lambda x: x["anomaly_score"], reverse=True)

# Save ranking
ranking_file = os.path.join(DATA_DIR, "classifier_ranking_v7.json")
with open(ranking_file, "w") as f:
    json.dump(ranking, f, indent=2)

print(f"  Saved: {ranking_file}")
print(f"\n  Top 20 Anomalies (likely pulsars/BH):")
for i, r in enumerate(ranking[:20]):
    print(f"    {i+1}. {r['anchor']}  (score={r['anomaly_score']:.4f}, prob={r['prob']:.4f}, pm={r['pm_total']:.1f})")

# ==========
# 6. Visualization
# ==========
print("\n--- 6. Visualization ---")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle("BlackHole Beacon — Anomaly Detection v7.0 (Isolation Forest)", fontsize=16)

# 1. Feature space (PCA)
ax = axes[0, 0]
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)
scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], c=probs, cmap='coolwarm', alpha=0.5, s=10)
ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
ax.set_title("Feature Space (PCA)")
plt.colorbar(scatter, ax=ax, label="Anomaly Probability")

# 2. Anomaly score distribution
ax = axes[0, 1]
ax.hist(scores, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
ax.set_xlabel("Anomaly Score")
ax.set_ylabel("Count")
ax.set_title("Anomaly Score Distribution")

# 3. Top 20 anomalies
ax = axes[0, 2]
top20 = ranking[:20]
anchors = [r["anchor"] for r in top20]
probs_top20 = [r["prob"] for r in top20]
ax.barh(range(len(anchors)), probs_top20)
ax.set_yticks(range(len(anchors)))
ax.set_yticklabels(anchors)
ax.set_xlabel("Anomaly Probability")
ax.set_title("Top 20 Anomalies (v7)")
ax.invert_yaxis()

# 4. Feature importance (PCA loadings)
ax = axes[1, 0]
feature_names = ["J-H", "H-K", "W1-W2", "W2-W3",
                 "pm_ra", "pm_dec", "abs(pm_ra)", "abs(pm_dec)", "pm_total"]
loadings = pd.DataFrame(
    pca.components_.T,
    columns=["PC1", "PC2"],
    index=feature_names
)
sns.heatmap(loadings, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
ax.set_title("PCA Loadings (Feature Importance)")

# 5. Probability vs. Phase 3 score
ax = axes[1, 1]
phase3_scores = [r["score_total"] for r in ranking]
anomaly_probs = [r["prob"] for r in ranking]
ax.scatter(phase3_scores, anomaly_probs, alpha=0.5, s=10)
ax.set_xlabel("Phase 3 Score")
ax.set_ylabel("Anomaly Probability")
ax.set_title("Anomaly Probability vs. Phase 3 Score")

# 6. Anomaly probability distribution
ax = axes[1, 2]
ax.hist(probs, bins=50, alpha=0.7, color='coral', edgecolor='black')
ax.set_xlabel("Anomaly Probability")
ax.set_ylabel("Count")
ax.set_title("Anomaly Probability Distribution")

plt.tight_layout()
plot_file = os.path.join(PLOT_DIR, "classifier_results_v7.png")
plt.savefig(plot_file, dpi=150)
plt.close()

print(f"  Saved: {plot_file}")

# ==========
# 7. Save model
# ==========
print("\n--- 7. Save Model ---")

import pickle
model_file = os.path.join(DATA_DIR, "classifier_model_v7.pkl")
with open(model_file, "wb") as f:
    pickle.dump({
        "model": iso_forest,
        "scaler": scaler,
        "feature_names": feature_names
    }, f)

print(f"  Saved: {model_file}")

# ==========
# 8. Summary
# ==========
print("\n" + "="*80)
print("BlackHole Beacon — Anomaly Detection v7.0 COMPLETE")
print("="*80)

print(f"\n  Candidates analyzed: {len(candidates)}")
print(f"  Contamination (assumed): 10%")
print(f"  Anomaly score range: [{scores.min():.4f}, {scores.max():.4f}]")

print(f"\n  Top 10 Anomalies:")
for i, r in enumerate(ranking[:10]):
    print(f"    {i+1}. {r['anchor']}  (score={r['anomaly_score']:.4f}, prob={r['prob']:.4f})")

print(f"\n  Files generated:")
print(f"    - {ranking_file}")
print(f"    - {plot_file}")
print(f"    - {model_file}")

print("\n" + "="*80)
print("DONE. Anomaly detection complete (unsupervised, no negative samples needed).")
print("="*80)
