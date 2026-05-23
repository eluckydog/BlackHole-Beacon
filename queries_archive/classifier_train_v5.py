"""
BlackHole Beacon — Classifier Training v5.0 (NO Phase3 scores)

Uses REAL negative samples (confusing sources) instead of synthetic ones.
REMOVED Phase 3 scores (features 10-14) to prevent cheating.
Now uses ONLY IR colors + PM (9 features).
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc
from sklearn.preprocessing import StandardScaler
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
print("BlackHole Beacon — Classifier Training v5.0 (NO Phase3 scores)")
print("="*80)

print("\n--- 1. Load Data ---")

# Load Phase3 candidates (positive samples)
# NOTE: phase3_candidates_full.json is a LIST of dicts
phase3_file = os.path.join(DATA_DIR, "phase3_candidates_full.json")
with open(phase3_file, "r") as f:
    candidates = json.load(f)  # Direct list of candidates

print(f"  Phase 3 candidates (full): {len(candidates)}")

# Load REAL negative samples
neg_file = os.path.join(DATA_DIR, "real_negative_samples_v4.json")
with open(neg_file, "r") as f:
    neg_data = json.load(f)

negative_samples = neg_data["samples"]
print(f"  Real negative samples: {len(negative_samples)}")
print(f"  Negative types: {neg_data['metadata']['types']}")

# ==========
# 2. Build feature matrix (NO Phase3 scores!)
# ==========
print("\n--- 2. Build Feature Matrix (NO Phase3 scores) ---")

def extract_features(candidate, is_positive=True):
    """Extract 9 features (NO Phase3 scores!)."""
    features = []
    
    # 1-4: IR colors (2MASS + WISE)
    if is_positive:
        # Positive: top-level keys (J, H, K, W1, W2)
        j = candidate.get("J", None)
        h = candidate.get("H", None)
        k = candidate.get("K", None)
        w1 = candidate.get("W1", None)
        w2 = candidate.get("W2", None)
        w3 = None  # Not available in phase3_candidates_full.json
    else:
        # Negative: from sample dict
        j = candidate.get("J", None)
        h = candidate.get("H", None)
        k = candidate.get("K", None)
        w1 = candidate.get("W1", None)
        w2 = candidate.get("W2", None)
        w3 = candidate.get("W3", None)
    
    # IR colors (handle missing values)
    j_h = (j - h) if (j is not None and h is not None) else 0.0
    h_k = (h - k) if (h is not None and k is not None) else 0.0
    w1_w2 = (w1 - w2) if (w1 is not None and w2 is not None) else 0.0
    w2_w3 = (w2 - w3) if (w2 is not None and w3 is not None) else 0.0
    
    features.extend([j_h, h_k, w1_w2, w2_w3])
    
    # 5-9: Proper motion (PM)
    if is_positive:
        # Positive: proper_motion_masyr is a SCALAR (total PM in mas/yr)
        pm_total = candidate.get("proper_motion_masyr", 0.0) or 0.0
        # Can't split into pm_ra, pm_dec (total only)
        pm_ra = 0.0
        pm_dec = 0.0
        abs_pm_ra = 0.0
        abs_pm_dec = 0.0
    else:
        # Negative: pm_ra, pm_dec are separate
        pm_ra = candidate.get("pm_ra", 0.0) or 0.0
        pm_dec = candidate.get("pm_dec", 0.0) or 0.0
        pm_total = (pm_ra**2 + pm_dec**2)**0.5
        abs_pm_ra = abs(pm_ra)
        abs_pm_dec = abs(pm_dec)
    
    features.extend([pm_ra, pm_dec, abs_pm_ra, abs_pm_dec, pm_total])
    
    # NO Phase 3 scores (removed to prevent cheating!)
    
    return features

# Build positive samples (TOP 500 by score)
positive = sorted(candidates, key=lambda x: x.get("scores", {}).get("total", 0), reverse=True)[:500]
print(f"  Positive samples (TOP 500): {len(positive)}")

X_pos = [extract_features(c, is_positive=True) for c in positive]
y_pos = [1] * len(X_pos)

# Build negative samples (all 1350 real negatives)
X_neg = [extract_features(s, is_positive=False) for s in negative_samples]
y_neg = [0] * len(X_neg)

# Combine
X = np.array(X_pos + X_neg)
y = np.array(y_pos + y_neg)

print(f"  Negative samples (real): {len(X_neg)}")
print(f"  Feature matrix: {X.shape}")
print(f"  Positive: {sum(y)} / Negative: {len(y) - sum(y)}")
print(f"  Features: 9 (IR colors 1-4, PM 5-9) — NO Phase3 scores!")

# ==========
# 3. Train classifier (5-fold CV)
# ==========
print("\n--- 3. Train Classifier (5-fold CV) ---")

# Standardize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Hyperparameter grid
param_grid = {
    "n_estimators": [50, 100, 200],
    "max_depth": [3, 5, 10, None],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4]
}

# Grid Search with 5-fold CV
print("  Running Grid Search (5-fold CV)...")
rf = RandomForestClassifier(random_state=42, n_jobs=-1)
grid_search = GridSearchCV(rf, param_grid, cv=5, scoring="roc_auc", n_jobs=-1, verbose=1)

grid_search.fit(X_scaled, y)

print(f"  Best parameters: {grid_search.best_params_}")
print(f"  Best CV AUC: {grid_search.best_score_:.4f}")

# ==========
# 4. Evaluation
# ==========
print("\n--- 4. Evaluation ---")

best_rf = grid_search.best_estimator_

# Cross-validation scores
cv_scores = cross_val_score(best_rf, X_scaled, y, cv=5, scoring="roc_auc")
print(f"  CV AUC scores: {cv_scores}")
print(f"  Mean AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# Feature importance
feature_names = ["J-H", "H-K", "W1-W2", "W2-W3",
                 "pm_ra", "pm_dec", "abs(pm_ra)", "abs(pm_dec)", "pm_total"]

importances = best_rf.feature_importances_
indices = np.argsort(importances)[::-1]

print("\n  Feature Importance:")
for i in range(len(feature_names)):
    print(f"    {feature_names[indices[i]]}: {importances[indices[i]]:.3f}")

# ==========
# 5. Rank all candidates
# ==========
print("\n--- 5. Rank All Candidates ---")

# Extract features for ALL candidates
X_all = [extract_features(c, is_positive=True) for c in candidates]
X_all = np.array(X_all)

# Standardize (using same scaler)
X_all_scaled = scaler.transform(X_all)

# Predict probabilities
probs = best_rf.predict_proba(X_all)[:, 1]  # Probability of class 1 (positive)

# Create ranking
ranking = []
for i, c in enumerate(candidates):
    rank = c.get("rank", i+1)
    anchor = c.get("anchor", f"UNK_{i}")
    designation = c.get("designation", "")
    
    ranking.append({
        "rank": rank,
        "anchor": anchor,
        "designation": designation,
        "prob": float(probs[i]),
        "score_total": c.get("scores", {}).get("total", 0.0),
        "pm_total": c.get("proper_motion_masyr", 0.0) or 0.0
    })

# Sort by probability (descending)
ranking = sorted(ranking, key=lambda x: x["prob"], reverse=True)

# Save ranking
ranking_file = os.path.join(DATA_DIR, "classifier_ranking_v5.json")
with open(ranking_file, "w") as f:
    json.dump(ranking, f, indent=2)

print(f"  Saved: {ranking_file}")
print(f"\n  Top 10 Candidates:")
for i, r in enumerate(ranking[:10]):
    print(f"    {i+1}. {r['anchor']}  (prob={r['prob']:.4f}, score={r['score_total']}, pm={r['pm_total']:.1f})")

# ==========
# 6. Visualization
# ==========
print("\n--- 6. Visualization ---")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle("BlackHole Beacon — Classifier Evaluation v5.0 (NO Phase3 scores)", fontsize=16)

# 1. Feature importance
ax = axes[0, 0]
ax.barh(range(len(feature_names)), importances[indices])
ax.set_yticks(range(len(feature_names)))
ax.set_yticklabels([feature_names[i] for i in indices])
ax.set_xlabel("Feature Importance")
ax.set_title("Feature Importance (9 features)")
ax.invert_yaxis()

# 2. CV AUC distribution
ax = axes[0, 1]
ax.boxplot([cv_scores], tick_labels=["CV AUC"])
ax.set_ylabel("AUC")
ax.set_title(f"CV AUC Distribution (Mean={cv_scores.mean():.4f})")

# 3. Top 20 candidates
ax = axes[0, 2]
top20 = ranking[:20]
anchors = [r["anchor"] for r in top20]
probs_top20 = [r["prob"] for r in top20]
ax.barh(range(len(anchors)), probs_top20)
ax.set_yticks(range(len(anchors)))
ax.set_yticklabels(anchors)
ax.set_xlabel("ML Probability")
ax.set_title("Top 20 Candidates (v5)")
ax.invert_yaxis()

# 4. Confusion matrix (on CV predictions)
ax = axes[1, 0]
from sklearn.model_selection import cross_val_predict
y_pred = cross_val_predict(best_rf, X_scaled, y, cv=5)
cm = confusion_matrix(y, y_pred)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax)
ax.set_xlabel("Predicted")
ax.set_ylabel("True")
ax.set_title("Confusion Matrix (5-fold CV)")

# 5. ROC curve
ax = axes[1, 1]
from sklearn.metrics import roc_curve, auc
y_pred_proba = cross_val_predict(best_rf, X_scaled, y, cv=5, method="predict_proba")
fpr, tpr, _ = roc_curve(y, y_pred_proba[:, 1])
roc_auc = auc(fpr, tpr)
ax.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC curve (AUC = {roc_auc:.4f})")
ax.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curve (5-fold CV)")
ax.legend(loc="lower right")

# 6. Probability distribution
ax = axes[1, 2]
probs_pos = best_rf.predict_proba(X_scaled[y==1])[:, 1]
probs_neg = best_rf.predict_proba(X_scaled[y==0])[:, 1]
ax.hist(probs_pos, bins=20, alpha=0.5, label="Positive (pulsar/BH)", color="red")
ax.hist(probs_neg, bins=20, alpha=0.5, label="Negative (confusing)", color="blue")
ax.set_xlabel("ML Probability")
ax.set_ylabel("Count")
ax.set_title("Probability Distribution")
ax.legend()

plt.tight_layout()
plot_file = os.path.join(PLOT_DIR, "classifier_results_v5.png")
plt.savefig(plot_file, dpi=150)
plt.close()

print(f"  Saved: {plot_file}")

# ==========
# 7. Save model
# ==========
print("\n--- 7. Save Model ---")

import pickle
model_file = os.path.join(DATA_DIR, "classifier_model_v5.pkl")
with open(model_file, "wb") as f:
    pickle.dump({
        "model": best_rf,
        "scaler": scaler,
        "feature_names": feature_names
    }, f)

print(f"  Saved: {model_file}")

# ==========
# 8. Summary
# ==========
print("\n" + "="*80)
print("BlackHole Beacon — Classifier Training v5.0 COMPLETE")
print("="*80)

print(f"\n  Positive samples: {len(positive)}")
print(f"  Negative samples: {len(negative_samples)} (REAL, from Simbad TAP)")
print(f"  CV AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
print(f"  Best params: {grid_search.best_params_}")
print(f"  Features: 9 (IR colors + PM only, NO Phase3 scores)")

print(f"\n  Top 5 Candidates:")
for i, r in enumerate(ranking[:5]):
    print(f"    {i+1}. {r['anchor']}  (prob={r['prob']:.4f})")

print(f"\n  Files generated:")
print(f"    - {ranking_file}")
print(f"    - {plot_file}")
print(f"    - {model_file}")

print("\n" + "="*80)
