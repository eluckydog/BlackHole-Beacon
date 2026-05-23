"""BlackHole Beacon — P2: Classifier Training v3.0
Improved: 1000 synthetic negatives + 5-fold CV + hyperparameter tuning.
"""

import json, os, sys, time, random
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, GridSearchCV, StratifiedKFold
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

print("BlackHole Beacon — P2: Classifier Training v3.0 (with CV)")
print("="*60)

# ==============================
# 1. Load Data
# ==============================
print("\n--- 1. Load Data ---")

# Positive samples: phase3 candidates (FULL, 1224 anchors)
p3_path = os.path.join(DATA_DIR, "phase3_candidates_full.json")
with open(p3_path) as f:
    phase3 = json.load(f)
print(f"  Phase 3 candidates (full): {len(phase3)}")

# Batch results (for match data)
batch_path = os.path.join(DATA_DIR, "batch_all_results.json")
with open(batch_path) as f:
    batch = json.load(f)
print(f"  Batch results: {len(batch)} anchors")

# ==============================
# 2. Build Feature Matrix
# ==============================
print("\n--- 2. Build Feature Matrix ---")

def extract_features(anchor_name, match_data):
    """Extract features for a single anchor-match pair."""
    feats = {}
    
    # Helper: get first match if list
    def _get(m, key):
        if key not in m:
            return None
        val = m[key]
        if isinstance(val, list) and len(val) > 0:
            return val[0]
        return val
    
    # Color features (from match_data)
    if "2mass" in match_data:
        m = match_data["2mass"]
        if isinstance(m, list) and len(m) > 0:
            m = m[0]
        if isinstance(m, dict):
            j = m.get("j_m") or m.get("J_mag")
            h = m.get("h_m") or m.get("H_mag")
            k = m.get("k_m") or m.get("K_mag")
            if j is not None and h is not None:
                feats["J-H"] = float(j) - float(h)
            if h is not None and k is not None:
                feats["H-K"] = float(h) - float(k)
            if j is not None and k is not None:
                feats["J-K"] = float(j) - float(k)
    
    if "wise" in match_data:
        w = match_data["wise"]
        if isinstance(w, list) and len(w) > 0:
            w = w[0]
        if isinstance(w, dict):
            w1 = w.get("w1_m") or w.get("W1_mag")
            w2 = w.get("w2_m") or w.get("W2_mag")
            w3 = w.get("w3_m") or w.get("W3_mag")
            if w1 is not None and w2 is not None:
                feats["W1-W2"] = float(w1) - float(w2)
            if w2 is not None and w3 is not None:
                feats["W2-W3"] = float(w2) - float(w3)
            if w1 is not None and w3 is not None:
                feats["W1-W3"] = float(w1) - float(w3)
    
    # Variability features (if available)
    if "proper_motion" in match_data:
        pm = match_data["proper_motion"]
        pm_ra = pm.get("pm_ra", 0) or 0
        pm_dec = pm.get("pm_dec", 0) or 0
        feats["pm_ra"] = abs(float(pm_ra))
        feats["pm_dec"] = abs(float(pm_dec))
        feats["pm_total"] = (feats["pm_ra"]**2 + feats["pm_dec"]**2)**0.5
    else:
        feats["pm_ra"] = 0.0
        feats["pm_dec"] = 0.0
        feats["pm_total"] = 0.0
    
    # Phase 3 scores (if available)
    if "score_total" in match_data:
        feats["score_total"] = match_data.get("score_total", 0) or 0
        feats["score_color"] = match_data.get("score_color", 0) or 0
        feats["score_variability"] = match_data.get("score_variability", 0) or 0
    else:
        feats["score_total"] = 0.0
        feats["score_color"] = 0.0
        feats["score_variability"] = 0.0
    
    # Default values for missing features
    for col in ["J-H", "H-K", "J-K", "W1-W2", "W2-W3", "W1-W3",
                "pm_ra", "pm_dec", "pm_total",
                "score_total", "score_color", "score_variability"]:
        if col not in feats:
            feats[col] = 0.0
    
    return feats

# Build positive samples (use TOP 500 phase3 candidates)
positive_features = []
positive_labels = []
positive_names = []

# Get match data for each candidate
anchor_to_match = {}
for a in batch:
    a_name = a.get("anchor", {}).get("name", "")
    if a_name:
        anchor_to_match[a_name] = a.get("matches", {})

for cand in phase3[:500]:  # Use TOP 500
    name = cand.get("anchor_name", "") or cand.get("anchor", "")
    if not name:
        continue
    
    match_data = anchor_to_match.get(name, {})
    feats = extract_features(name, match_data)
    positive_features.append(feats)
    positive_labels.append(1)  # Positive
    positive_names.append(name)

print(f"  Positive samples: {len(positive_features)}")

# Build NEGATIVE samples (1000 synthetic)
print("  Generating 1000 synthetic negative samples...")
random.seed(42)
np.random.seed(42)

negative_features = []
negative_labels = []
negative_names = []

for i in range(1000):
    # Random normal star colors (main sequence)
    feats = {
        "J-H": random.uniform(-0.1, 0.8),   # Normal stars
        "H-K": random.uniform(-0.05, 0.3),
        "J-K": random.uniform(0.0, 1.2),
        "W1-W2": random.uniform(-0.1, 0.5),  # Normal stars
        "W2-W3": random.uniform(0.0, 2.0),
        "W1-W3": random.uniform(0.0, 2.5),
        "pm_ra": random.uniform(0, 20),      # Low proper motion
        "pm_dec": random.uniform(0, 20),
        "pm_total": random.uniform(0, 28),
        "score_total": 0.0,                # No anomaly score
        "score_color": 0.0,
        "score_variability": 0.0,
    }
    negative_features.append(feats)
    negative_labels.append(0)  # Negative
    negative_names.append(f"neg_{i:04d}")

print(f"  Negative samples (synthetic): {len(negative_features)}")

# Combine
X_features = positive_features + negative_features
y = positive_labels + negative_labels
names = positive_names + negative_names

# Convert to DataFrame
feature_names = ["J-H", "H-K", "J-K", "W1-W2", "W2-W3", "W1-W3",
               "pm_ra", "pm_dec", "pm_total",
               "score_total", "score_color", "score_variability"]

X_df = pd.DataFrame(X_features)
X = X_df[feature_names].values

print(f"\n  Feature matrix: ({len(X)}, {len(feature_names)})")
print(f"  Positive: {sum(y)} / Negative: {len(y) - sum(y)}")

# ==============================
# 3. Train with Cross-Validation
# ==============================
print("\n--- 3. Train Classifier (5-fold CV) ---")

# Stratified K-Fold
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Hyperparameter grid
param_grid = {
    "n_estimators": [100, 200, 500],
    "max_depth": [5, 10, 20, None],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
}

# Grid search with CV
rf = RandomForestClassifier(random_state=42, n_jobs=-1)
grid_search = GridSearchCV(rf, param_grid, cv=skf, scoring="roc_auc", n_jobs=-1, verbose=1)

print("  Running Grid Search (5-fold CV)...")
grid_search.fit(X, y)

print(f"\n  Best parameters: {grid_search.best_params_}")
print(f"  Best CV AUC: {grid_search.best_score_:.4f}")

# Train final model with best params
best_rf = grid_search.best_estimator_
best_rf.fit(X, y)

# ==============================
# 4. Evaluate
# ==============================
print("\n--- 4. Evaluation ---")

# Cross-val scores
cv_scores = cross_val_score(best_rf, X, y, cv=skf, scoring="roc_auc")
print(f"  CV AUC scores: {cv_scores}")
print(f"  Mean AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# Feature importance
importances = best_rf.feature_importances_
indices = np.argsort(importances)[::-1]

print(f"\n  Feature Importance:")
for f in range(len(feature_names)):
    print(f"    {feature_names[indices[f]]:15s}: {importances[indices[f]]:.3f}")

# ==============================
# 5. Rank All Candidates
# ==============================
print("\n--- 5. Rank All Candidates ---")

# Predict probabilities for ALL phase3 candidates
all_probs = []
for cand in phase3:
    name = cand.get("anchor_name", "") or cand.get("anchor", "")
    if not name:
        continue
    
    match_data = anchor_to_match.get(name, {})
    feats = extract_features(name, match_data)
    X_cand = np.array([[feats.get(f, 0.0) for f in feature_names]])
    prob = best_rf.predict_proba(X_cand)[0][1]  # Probability of class 1
    all_probs.append({"name": name, "prob": prob, "cand": cand})

# Sort by probability
all_probs.sort(key=lambda x: x["prob"], reverse=True)

# Save ranking
ranking_path = os.path.join(DATA_DIR, "classifier_ranking_v3.json")
with open(ranking_path, "w") as f:
    json.dump([{"rank": i+1, "name": p["name"], "prob": p["prob"]} 
              for i, p in enumerate(all_probs)], f, indent=2)
print(f"  Saved: {ranking_path}")

# ==============================
# 6. Visualization
# ==============================
print("\n--- 6. Visualization ---")

plots_dir = os.path.join(DATA_DIR, "plots")
os.makedirs(plots_dir, exist_ok=True)

# Figure: 2x3 subplots
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle("BlackHole Beacon — Classifier Training v3.0 (with CV)", fontsize=16, fontweight="bold")

# 1. Feature Importance
ax = axes[0, 0]
ax.barh(range(len(feature_names)), importances[indices])
ax.set_yticks(range(len(feature_names)))
ax.set_yticklabels([feature_names[i] for i in indices])
ax.set_xlabel("Importance")
ax.set_title("Feature Importance (Random Forest)")
ax.invert_yaxis()

# 2. CV AUC distribution
ax = axes[0, 1]
ax.boxplot([cv_scores], vert=False)
ax.set_xlabel("AUC")
ax.set_title(f"5-Fold CV AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")
ax.set_yticks([])

# 3. Probability distribution
ax = axes[0, 2]
probs_pos = [p for p, l in zip(best_rf.predict_proba(X)[:, 1], y) if l == 1]
probs_neg = [p for p, l in zip(best_rf.predict_proba(X)[:, 1], y) if l == 0]
ax.hist(probs_pos, bins=20, alpha=0.5, label="Positive", color="red")
ax.hist(probs_neg, bins=20, alpha=0.5, label="Negative", color="blue")
ax.set_xlabel("Predicted Probability")
ax.set_ylabel("Count")
ax.set_title("Probability Distribution")
ax.legend()

# 4. Top 20 candidates
ax = axes[1, 0]
top20 = all_probs[:20]
names_top = [p["name"][:10] for p in top20]
probs_top = [p["prob"] for p in top20]
ax.barh(range(20), probs_top)
ax.set_yticks(range(20))
ax.set_yticklabels(names_top)
ax.set_xlabel("ML Probability")
ax.set_title("Top 20 Candidates (ML Probability)")
ax.invert_yaxis()

# 5. Confusion Matrix (on CV predictions)
ax = axes[1, 1]
from sklearn.metrics import confusion_matrix
y_pred = best_rf.predict(X)
cm = confusion_matrix(y, y_pred)
im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
ax.set_title("Confusion Matrix (Training)")
ax.set_ylabel("True")
ax.set_xlabel("Predicted")
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.text(0.5, 0.5, str(cm[0, 0]), ha="center", va="center", color="white" if cm[0, 0] > cm.max()/2 else "black")
ax.text(1.5, 0.5, str(cm[0, 1]), ha="center", va="center", color="white" if cm[0, 1] > cm.max()/2 else "black")
ax.text(0.5, 1.5, str(cm[1, 0]), ha="center", va="center", color="white" if cm[1, 0] > cm.max()/2 else "black")
ax.text(1.5, 1.5, str(cm[1, 1]), ha="center", va="center", color="white" if cm[1, 1] > cm.max()/2 else "black")

# 6. ROC Curve (approximate)
ax = axes[1, 2]
from sklearn.metrics import roc_curve
y_prob = best_rf.predict_proba(X)[:, 1]
fpr, tpr, _ = roc_curve(y, y_prob)
ax.plot(fpr, tpr, label=f"ROC (AUC={roc_auc_score(y, y_prob):.3f})")
ax.plot([0, 1], [0, 1], "k--")
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curve (Training)")
ax.legend()

plt.tight_layout()
plot_path = os.path.join(plots_dir, "classifier_results_v3.png")
plt.savefig(plot_path, dpi=150)
plt.close()
print(f"  Saved: {plot_path}")

# ==============================
# 7. Save Model
# ==============================
print("\n--- 7. Save Model ---")

import pickle
model_path = os.path.join(DATA_DIR, "classifier_model_v3.pkl")
with open(model_path, "wb") as f:
    pickle.dump(best_rf, f)
print(f"  Saved: {model_path}")

# ==============================
# 8. Summary
# ==============================
print("\n" + "="*60)
print("BlackHole Beacon — P2: Classifier Training v3.0 COMPLETE")
print("="*60)
print(f"\n  Positive samples: {len(positive_features)}")
print(f"  Negative samples: {len(negative_features)}")
print(f"  CV AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
print(f"  Best params: {grid_search.best_params_}")
print(f"\n  Top 5 Candidates:")
for i, p in enumerate(all_probs[:5]):
    print(f"    {i+1}. {p['name']:20s} (prob={p['prob']:.4f})")

print(f"\n  Files generated:")
print(f"    - {ranking_path}")
print(f"    - {plot_path}")
print(f"    - {model_path}")
print("\nDone.")
