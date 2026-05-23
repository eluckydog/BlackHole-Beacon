"""BlackHole Beacon — Task 3: Classifier Training

Improved negative samples: sample 1000 normal stars from 2MASS/WISE.
Train a classifier to rank candidates.
"""

import json, os, sys, time, random
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
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

print("BlackHole Beacon — Task 3: Classifier Training")
print("="*60)

# ==============================
# 1. Load data
# ==============================
print("\n--- 1. Load Data ---")

# Positive samples: anchors with matches
with open(os.path.join(DATA_DIR, "batch_all_results.json")) as f:
    batch = json.load(f)
print(f"  Batch results: {len(batch)} anchors")

# Phase 3 candidates
with open(os.path.join(DATA_DIR, "phase3_candidates.json")) as f:
    phase3 = json.load(f)
print(f"  Phase 3 candidates: {len(phase3)}")

# Negative samples (if available)
neg_path = os.path.join(DATA_DIR, "negative_samples.json")
negative_samples = []
if os.path.exists(neg_path):
    with open(neg_path) as f:
        neg_data = json.load(f)
        negative_samples = neg_data.get("random_positions", [])
        # Also check other keys
        for key in neg_data:
            if isinstance(neg_data[key], list):
                negative_samples.extend(neg_data[key])
print(f"  Negative samples (file): {len(negative_samples)}")

# ==============================
# 2. Build feature matrix
# ==============================
print("\n--- 2. Build Feature Matrix ---")

def extract_features(anchor_name, match_data):
    """Extract features for a single anchor-match pair."""
    feats = {}
    
    # Helper: get first match if list, else return as-is
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
            m = m[0]  # Take first match
        if isinstance(m, dict):
            j = m.get("J_mag")
            h = m.get("H_mag")
            k = m.get("K_mag")
            if j is not None and h is not None:
                feats["J-H"] = j - h
            if h is not None and k is not None:
                feats["H-K"] = h - k
            if j is not None and k is not None:
                feats["J-K"] = j - k
    
    if "wise" in match_data:
        w = match_data["wise"]
        if isinstance(w, list) and len(w) > 0:
            w = w[0]
        if isinstance(w, dict):
            w1 = w.get("W1_mag")
            w2 = w.get("W2_mag")
            w3 = w.get("W3_mag")
            if w1 is not None and w2 is not None:
                feats["W1-W2"] = w1 - w2
            if w2 is not None and w3 is not None:
                feats["W2-W3"] = w2 - w3
            if w1 is not None and w3 is not None:
                feats["W1-W3"] = w1 - w3
    
    # Variability features (if available)
    if "variability" in match_data:
        v = match_data["variability"]
        feats["pm_ra"] = v.get("pm_ra", 0) or 0
        feats["pm_dec"] = v.get("pm_dec", 0) or 0
        feats["pm_total"] = ((feats["pm_ra"]**2 + feats["pm_dec"]**2)**0.5) if (feats["pm_ra"] or feats["pm_dec"]) else 0
    
    # SED features (if available)
    if "sed" in match_data:
        s = match_data["sed"]
        feats["bb_temp"] = s.get("bb_temperature_K", 0) or 0
        feats["pl_index"] = s.get("powerlaw_index", 0) or 0
    
    # Default values for missing features
    for col in ["J-H", "H-K", "J-K", "W1-W2", "W2-W3", "W1-W3",
                "pm_ra", "pm_dec", "pm_total", "bb_temp", "pl_index"]:
        if col not in feats:
            feats[col] = 0.0
    
    return feats

# Build positive samples (anchors with matches)
positive_features = []
positive_labels = []
positive_names = []

# Use ALL phase3 candidates as positive samples (removed score filter)
for cand in phase3[:300]:  # Use up to 300
    name = cand.get("anchor", "")
    if not name:
        continue
    
    # Find match data from batch results
    match_data = {}
    for a in batch:
        a_anchor = a.get("anchor", {})
        if isinstance(a_anchor, dict):
            a_name = a_anchor.get("name", "")
        else:
            a_name = str(a_anchor)
        if a_name == name:
            match_data = a.get("matches", {})
            break
    
    feats = extract_features(name, match_data)
    positive_features.append(feats)
    positive_labels.append(1)  # Positive
    positive_names.append(name)

print(f"  Positive samples: {len(positive_features)}")

# If still 0, use anchor catalogs directly
if len(positive_features) == 0:
    print("  No phase3 candidates found, using anchor catalogs directly...")
    import csv
    for fname in ["psrcat_catalog.csv", "bh_xrb_catalog.csv"]:
        fpath = os.path.join(CATALOG_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = (row.get("JName") or row.get("Name") or "").strip()
                if not name:
                    continue
                # Use default features (will be filled with 0s)
                feats = extract_features(name, {})
                positive_features.append(feats)
                positive_labels.append(1)
                positive_names.append(name)
    print(f"  Positive samples (from catalogs): {len(positive_features)}")

# Build negative samples (random matches or normal stars)
negative_features = []
negative_labels = []
negative_names = []

# Use negative_samples.json if available
if negative_samples and len(negative_samples) > 10:
    for sample in negative_samples[:200]:
        name = sample.get("anchor", "RAND")
        match_data = sample.get("match", {})
        feats = extract_features(name, match_data)
        negative_features.append(feats)
        negative_labels.append(0)  # Negative
        negative_names.append(name)
    print(f"  Negative samples (from file): {len(negative_features)}")
else:
    # Generate synthetic negative samples from random 2MASS/WISE positions
    print("  Generating synthetic negative samples...")
    random.seed(42)
    for i in range(500):
        # Random normal star colors (main sequence)
        feats = {
            "J-H": random.uniform(-0.1, 0.8),   # Normal stars
            "H-K": random.uniform(-0.05, 0.3),
            "J-K": random.uniform(0.0, 1.2),
            "W1-W2": random.uniform(-0.1, 0.5),  # Normal stars
            "W2-W3": random.uniform(-0.1, 1.0),
            "W1-W3": random.uniform(0.0, 1.5),
            "pm_ra": random.uniform(-50, 50),    # Normal proper motion
            "pm_dec": random.uniform(-50, 50),
            "pm_total": random.uniform(0, 70),
            "bb_temp": random.uniform(3000, 10000),  # Normal star temps
            "pl_index": 0.0,  # No power-law
        }
        negative_features.append(feats)
        negative_labels.append(0)  # Negative
        negative_names.append(f"SYNTH_{i}")
    print(f"  Negative samples (synthetic): {len(negative_features)}")

print(f"  Total samples: {len(positive_features) + len(negative_features)}")

# ==============================
# 3. Train classifier
# ==============================
print("\n--- 3. Train Classifier ---")

# Combine features
all_features = positive_features + negative_features
all_labels = positive_labels + negative_labels

# Convert to DataFrame
feature_names = ["J-H", "H-K", "J-K", "W1-W2", "W2-W3", "W1-W3",
                 "pm_ra", "pm_dec", "pm_total", "bb_temp", "pl_index"]
df = pd.DataFrame(all_features, columns=feature_names)
X = df.values
y = np.array(all_labels)

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

for cand in phase3:
    name = cand.get("anchor", "")
    score = cand.get("score", 0)
    
    # Find match data
    match_data = {}
    for a in batch:
        if a.get("anchor") == name or a.get("name") == name:
            match_data = a.get("matches", {})
            break
    
    feats = extract_features(name, match_data)
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
out_file = os.path.join(OUT_DIR, "classifier_ranking.json")
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
plot_file = os.path.join(OUT_DIR, "plots", "classifier_results.png")
os.makedirs(os.path.join(OUT_DIR, "plots"), exist_ok=True)
plt.savefig(plot_file, dpi=150)
print(f"\n  Saved: {plot_file}")

print("\nDone.")
