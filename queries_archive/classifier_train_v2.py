"""BlackHole Beacon — Task 3: Classifier Training v2

Use phase3_candidates.json directly (has J,H,K,W1,W2 columns).
Train a classifier to rank candidates.
"""

import json, os, sys, time, random
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
CATALOG_DIR = os.path.join(ROOT, "catalog")
OUT_DIR = DATA_DIR
os.makedirs(OUT_DIR, exist_ok=True)

print("BlackHole Beacon — Task 3: Classifier Training v2")
print("="*60)

# ==============================
# 1. Load data
# ==============================
print("\n--- 1. Load Data ---")

# Phase 3 candidates (already have J,H,K,W1,W2)
with open(os.path.join(DATA_DIR, "phase3_candidates.json")) as f:
    phase3 = json.load(f)
print(f"  Phase3 candidates: {len(phase3)}")

# Anchor catalogs (positive labels)
print("  Loading anchor catalogs (positive labels)...")
anchor_names = set()
import csv
for fname in ["psrcat_catalog.csv", "bh_xrb_catalog.csv", "smbh_catalog.csv"]:
    fpath = os.path.join(CATALOG_DIR, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("JName") or row.get("Name") or "").strip()
            if name:
                anchor_names.add(name)
print(f"  Anchor names (positive): {len(anchor_names)}")

# Negative samples (from file)
neg_path = os.path.join(DATA_DIR, "negative_samples.json")
negative_matches = []
if os.path.exists(neg_path):
    with open(neg_path) as f:
        neg_data = json.load(f)
        # Collect all matches from negative_samples.json
        for key in neg_data:
            if isinstance(neg_data[key], list):
                for item in neg_data[key]:
                    if "match" in item:
                        negative_matches.append(item["match"])
print(f"  Negative matches (from file): {len(negative_matches)}")

# ==============================
# 2. Build feature matrix
# ==============================
print("\n--- 2. Build Feature Matrix ---")

def extract_features_from_phase3(entry):
    """Extract features directly from phase3 entry (has J,H,K,W1,W2)."""
    feats = {}
    
    # Colors from phase3 entry
    J = entry.get("J")
    H = entry.get("H")
    K = entry.get("K")
    W1 = entry.get("W1")
    W2 = entry.get("W2")
    
    if J is not None and H is not None:
        feats["J-H"] = J - H
    if H is not None and K is not None:
        feats["H-K"] = H - K
    if J is not None and K is not None:
        feats["J-K"] = J - K
    
    if W1 is not None and W2 is not None:
        feats["W1-W2"] = W1 - W2
    # W2-W3 not available in phase3 (need W3)
    feats["W2-W3"] = 0.0
    feats["W1-W3"] = 0.0
    
    # Proper motion
    pm = entry.get("proper_motion_masyr", 0) or 0
    feats["pm_total"] = pm
    
    # Phase 3 score components (useful features)
    scores = entry.get("scores", {})
    feats["score_anchor_type"] = scores.get("anchor_type", 0) or 0
    feats["score_brightness"] = scores.get("brightness", 0) or 0
    feats["score_color"] = scores.get("color", 0) or 0
    feats["score_variability"] = scores.get("variability", 0) or 0
    feats["score_total"] = scores.get("total", 0) or 0
    
    # Default values for missing features
    for col in ["J-H", "H-K", "J-K", "W1-W2", "W2-W3", "W1-W3",
                "pm_total", "score_anchor_type", "score_brightness",
                "score_color", "score_variability", "score_total"]:
        if col not in feats:
            feats[col] = 0.0
    
    return feats

# Build positive samples (labeled by anchor catalogs)
positive_features = []
positive_labels = []
positive_names = []

for entry in phase3:
    name = entry.get("anchor", "")
    if not name:
        continue
    
    # Label: 1 if in anchor_names, else 0 (unlabeled -> use as negative for training)
    # Actually: we only know anchors are positive. Others are unlabeled.
    # For training: use anchor matches as positive, negative_samples as negative
    if name in anchor_names:
        label = 1
    else:
        label = 0  # Treat as negative for training (semi-supervised)
    
    feats = extract_features_from_phase3(entry)
    positive_features.append(feats)
    positive_labels.append(label)
    positive_names.append(name)

print(f"  Total phase3 entries: {len(positive_features)}")
print(f"  Positive (anchor match): {sum(positive_labels)}")
print(f"  Negative (unlabeled): {len(positive_labels) - sum(positive_labels)}")

# Build negative samples (from negative_samples.json)
negative_features = []
negative_labels = []
negative_names = []

# Use negative_matches (from file)
for i, match in enumerate(negative_matches[:200]):  # Limit to 200
    # Extract features from match (if it has J,H,K,W1,W2)
    feats = {}
    # Negative matches might have different structure
    # Just use default features
    for col in ["J-H", "H-K", "J-K", "W1-W2", "W2-W3", "W1-W3",
                "pm_total", "score_anchor_type", "score_brightness",
                "score_color", "score_variability", "score_total"]:
        feats[col] = 0.0  # Default (normal star)
    negative_features.append(feats)
    negative_labels.append(0)  # Negative
    negative_names.append(f"NEG_{i}")

print(f"  Negative samples (from file): {len(negative_features)}")

# If not enough negative samples, generate synthetic ones
if len(negative_features) < 100:
    print("  Generating synthetic negative samples...")
    random.seed(42)
    for i in range(300):
        feats = {
            "J-H": random.uniform(-0.1, 0.8),
            "H-K": random.uniform(-0.05, 0.3),
            "J-K": random.uniform(0.0, 1.2),
            "W1-W2": random.uniform(-0.1, 0.5),
            "W2-W3": random.uniform(-0.1, 1.0),
            "W1-W3": random.uniform(0.0, 1.5),
            "pm_total": random.uniform(0, 50),
            "score_anchor_type": 0,
            "score_brightness": random.uniform(0, 2),
            "score_color": 0,
            "score_variability": 0,
            "score_total": random.uniform(0, 5),
        }
        negative_features.append(feats)
        negative_labels.append(0)
        negative_names.append(f"SYNTH_{i}")
    print(f"  Synthetic negative samples: 300")

print(f"\n  Total samples: {len(positive_features) + len(negative_features)}")

# ==============================
# 3. Train classifier
# ==============================
print("\n--- 3. Train Classifier ---")

# Combine features
all_features = positive_features + negative_features
all_labels = np.array(positive_labels + negative_labels)

# Convert to DataFrame
feature_names = ["J-H", "H-K", "J-K", "W1-W2", "W2-W3", "W1-W3",
                 "pm_total", "score_anchor_type", "score_brightness",
                 "score_color", "score_variability", "score_total"]
df = pd.DataFrame(all_features, columns=feature_names)
X = df.values
y = all_labels

print(f"  Feature matrix: {X.shape}")
print(f"  Positive: {sum(y)} / Negative: {len(y)-sum(y)}")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

# Train Random Forest
print("\n  Training Random Forest...")
clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
clf.fit(X_train, y_train)

# Evaluate
y_pred = clf.predict(X_test)
y_prob = clf.predict_proba(X_test)[:, 1]

print("\n  Classification Report:")
print(classification_report(y_test, y_pred, target_names=["Negative", "Positive"]))

auc = roc_auc_score(y_test, y_prob)
print(f"  AUC: {auc:.3f}")

# Feature importance
print("\n  Feature Importance:")
importances = clf.feature_importances_
for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
    print(f"    {name}: {imp:.3f}")

# ==============================
# 4. Rank all candidates
# ==============================
print("\n--- 4. Rank All Candidates ---")

# Prepare all phase3 candidates
all_cand_features = []
all_cand_names = []
all_cand_scores = []

for entry in phase3:
    name = entry.get("anchor", "")
    score = entry.get("scores", {}).get("total", 0) or 0
    
    feats = extract_features_from_phase3(entry)
    all_cand_features.append(feats)
    all_cand_names.append(name)
    all_cand_scores.append(score)

# Predict probabilities
df_cand = pd.DataFrame(all_cand_features, columns=feature_names)
X_cand = df_cand.values
probs = clf.predict_proba(X_cand)[:, 1]

# Combine with phase3 scores
results = []
for i, (name, score, prob) in enumerate(zip(all_cand_names, all_cand_scores, probs)):
    results.append({
        "anchor": name,
        "phase3_score": score,
        "ml_probability": float(prob),
        "combined_score": 0.5 * score + 0.5 * prob * 14,  # Scale prob to similar range
    })

# Sort by combined score
results.sort(key=lambda x: x["combined_score"], reverse=True)

# Save results
out_file = os.path.join(OUT_DIR, "classifier_ranking_v2.json")
with open(out_file, "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\n  Saved: {out_file}")

# Print top 20
print("\n--- Top 20 Candidates (Combined Score) ---")
print(f"{'Rank':<5} {'Anchor':<20} {'Phase3':<8} {'ML Prob':<10} {'Combined':<10}")
print("-" * 60)
for i, r in enumerate(results[:20]):
    print(f"{i+1:<5} {r['anchor']:<20} {r['phase3_score']:<8.1f} {r['ml_probability']:<10.3f} {r['combined_score']:<10.1f}")

# ==============================
# 5. Visualize
# ==============================
print("\n--- 5. Visualize ---")

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 1. Feature importance
ax = axes[0, 0]
ax.barh(feature_names, clf.feature_importances_)
ax.set_xlabel("Importance")
ax.set_title("Feature Importance (Random Forest)")

# 2. Probability distribution
ax = axes[0, 1]
ax.hist(probs, bins=20, alpha=0.7, edgecolor="black")
ax.set_xlabel("ML Probability")
ax.set_ylabel("Count")
ax.set_title("Candidate Probability Distribution")

# 3. Score comparison
ax = axes[1, 0]
phase3_scores = [r["phase3_score"] for r in results]
ml_probs = [r["ml_probability"] for r in results]
ax.scatter(phase3_scores, ml_probs, alpha=0.5)
ax.set_xlabel("Phase 3 Score")
ax.set_ylabel("ML Probability")
ax.set_title("Phase 3 Score vs ML Probability")

# 4. Top 10 candidates
ax = axes[1, 1]
top10_names = [r["anchor"][:10] for r in results[:10]]
top10_scores = [r["combined_score"] for r in results[:10]]
ax.barh(range(10), top10_scores)
ax.set_yticks(range(10))
ax.set_yticklabels(top10_names)
ax.invert_yaxis()
ax.set_xlabel("Combined Score")
ax.set_title("Top 10 Candidates")

plt.tight_layout()
plot_file = os.path.join(OUT_DIR, "plots", "classifier_results_v2.png")
os.makedirs(os.path.join(OUT_DIR, "plots"), exist_ok=True)
plt.savefig(plot_file, dpi=150)
print(f"\n  Saved: {plot_file}")

print("\nDone.")
