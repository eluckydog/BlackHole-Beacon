"""BlackHole Beacon — Spectral Classifier v1.0

Trains a classifier on known pulsar SED features so that future
survey data can be scanned for pulsar/BH candidates by spectral similarity.

Pipeline:
  1. Feature engineering from multi-band photometry
  2. t-SNE embedding for visualization
  3. Random Forest classifier + anomaly detector
  4. Demonstrate classification on mock unknown sources
"""

import json, os, sys, math
import random
from datetime import datetime
from collections import defaultdict

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False
    print("WARNING: numpy not installed - install with 'pip install numpy scikit-learn'")

try:
    from sklearn.ensemble import RandomForestClassifier, IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("WARNING: scikit-learn not installed - will use simplified version")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES_FILE = os.path.join(ROOT, "data", "spectral_features.json")
OUTPUT = os.path.join(ROOT, "data", "classifier_model.json")
REPORT = os.path.join(ROOT, "data", "classifier_report.md")

with open(FEATURES_FILE) as f:
    spectral_db = json.load(f)

print("BlackHole Beacon — Spectral Classifier")
print("=" * 55)

# ==============================
# 1. Feature engineering
# ==============================

def extract_feature_vector(s):
    """Convert spectral entry to feature vector.
    Features: magnitudes, colors, spectral indices, all as floats."""
    features = {
        "J": s.get("J"),
        "H": s.get("H"),
        "K": s.get("K"),
        "W1": s.get("W1"),
        "W2": s.get("W2"),
        "W3": s.get("W3"),
        "W4": s.get("W4"),
        "J-H": s.get("J-H"),
        "H-K": s.get("H-K"),
        "W1-W2": s.get("W1-W2"),
        "W2-W3": s.get("W2-W3"),
        "alpha_JK": s.get("alpha_JK"),
        "alpha_W12": s.get("alpha_W12"),
        "alpha_JW1": s.get("alpha_JW1"),
        "pm": s.get("max_proper_motion_masyr"),
    }
    # Remove None values
    return {k: v for k, v in features.items() if v is not None}

# Define full feature set for matrix
ALL_FEATURES = ["J", "H", "K", "W1", "W2", "J-H", "H-K", "W1-W2", "W2-W3",
                "alpha_JK", "alpha_W12", "alpha_JW1", "pm"]

# Build feature matrix and labels
X_raw = []
labels = []
names = []
n_features = len(ALL_FEATURES)

for s in spectral_db:
    v = extract_feature_vector(s)
    # Only include entries with at least 4 features
    row = [v.get(f) for f in ALL_FEATURES]
    n_present = sum(1 for r in row if r is not None)
    if n_present >= 4:
        X_raw.append(row)
        labels.append(s["type"])
        names.append(s["anchor"])

print(f"\nFeature matrix: {len(X_raw)} samples x {n_features} features")
print(f"  Classes: {set(labels)}")

# Fill missing values with column median
X_filled = []
for row in X_raw:
    filled = []
    for col_idx in range(n_features):
        val = row[col_idx]
        if val is None:
            # Use column median
            col_vals = [X_raw[r][col_idx] for r in range(len(X_raw))
                       if X_raw[r][col_idx] is not None]
            if col_vals:
                col_vals.sort()
                val = col_vals[len(col_vals)//2]
            else:
                val = 0
        filled.append(val)
    X_filled.append(filled)

# ==============================
# 2. Embedding (PCA)
# ==============================

if HAS_NP and HAS_SKLEARN:
    X = np.array(X_filled)
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # PCA
    pca = PCA(n_components=min(3, len(X_scaled)))
    X_pca = pca.fit_transform(X_scaled)
    
    print(f"\nPCA variance explained: {[f'{v:.1%}' for v in pca.explained_variance_ratio_]}")
    print(f"  Total: {sum(pca.explained_variance_ratio_):.1%}")
    
    # ==============================
    # 3. Classification
    # ==============================
    
    # Train Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_scaled, labels)
    
    # Feature importance
    importance = list(zip(ALL_FEATURES, rf.feature_importances_))
    importance.sort(key=lambda x: -x[1])
    
    print(f"\n--- Feature Importance (Random Forest) ---")
    for feat, imp in importance[:10]:
        print(f"  {feat:12s}: {imp:.3f}")
    
    # ==============================
    # 4. Anomaly detection
    # ==============================
    
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    anomalies = iso_forest.fit_predict(X_scaled)
    # -1 = anomaly, 1 = normal
    
    anomaly_indices = [i for i, a in enumerate(anomalies) if a == -1]
    print(f"\n--- Anomaly Detection ---")
    print(f"  Anomalous sources: {len(anomaly_indices)} ({len(anomaly_indices)/len(X_scaled):.1%})")
    
    for idx in anomaly_indices[:10]:
        s = spectral_db[idx]
        flags = s.get("flags", [])
        print(f"  {s['anchor']:20s} ({s['type']:6s})  flags={flags}")
    
    # ==============================
    # 5. Model export for future use
    # ==============================
    
    model_data = {
        "features": ALL_FEATURES,
        "feature_importance": dict(importance),
        "n_samples": len(X_scaled),
        "classes": sorted(set(labels)),
        "pca_explained_variance": [float(v) for v in pca.explained_variance_ratio_],
        "anomaly_indices": anomaly_indices,
        "anomaly_names": [spectral_db[i]["anchor"] for i in anomaly_indices],
        "train_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scaling_means": [float(m) for m in scaler.mean_],
        "scaling_scales": [float(s) for s in scaler.scale_],
        "pca_components": [[float(c) for c in comp] for comp in pca.components_],
    }
    
    # Save model metadata
    with open(OUTPUT, "w") as f:
        json.dump(model_data, f, indent=2)
    print(f"\nModel: {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")
    
    # ==============================
    # 6. Demo: classify a mock unknown source
    # ==============================
    
    print(f"\n--- Demo: Classify Mock Unknown Sources ---")
    
    # Mock source 1: typical pulsar (like median of our sample)
    # Mock source 2: weird object (extreme colors)
    # Mock source 3: normal star (flat colors)
    mock_sources = [
        {
            "name": "MOCK_STAR (typical)",
            "J": 14.5, "H": 14.0, "K": 13.8,
            "W1": 14.0, "W2": 14.1,
            "J-H": 0.5, "H-K": 0.2, "W1-W2": -0.1,
            "alpha_JK": 0.3, "alpha_W12": 2.1,
            "pm": 0,
        },
        {
            "name": "MOCK_WEIRD (extreme)",
            "J": 18.0, "H": 16.5, "K": 15.0,
            "W1": 8.0, "W2": 6.5,
            "J-H": 1.5, "H-K": 1.5, "W1-W2": 1.5,
            "alpha_JK": 1.8, "alpha_W12": 0.5,
            "pm": 100,
        },
        {
            "name": "MOCK_FLAT (normal star)",
            "J": 12.0, "H": 11.5, "K": 11.3,
            "W1": 11.0, "W2": 10.9,
            "J-H": 0.5, "H-K": 0.2, "W1-W2": 0.1,
            "alpha_JK": 2.0, "alpha_W12": 2.0,
            "pm": 5,
        },
    ]
    
    for mock in mock_sources:
        vec = [mock.get(f, 0) for f in ALL_FEATURES]
        vec_scaled = scaler.transform([vec])
        
        # Classify
        pred = rf.predict(vec_scaled)[0]
        proba = rf.predict_proba(vec_scaled)[0]
        confidence = max(proba)
        n_neighbors = sum(1 for p in proba if p > 0.05)
        
        # Anomaly score
        anom_score = iso_forest.decision_function(vec_scaled)[0]
        is_anomaly = "ANOMALY" if anom_score < 0 else "normal"
        
        print(f"\n  {mock['name']}")
        print(f"    Predicted: {pred} (conf={confidence:.1%}, classes={n_neighbors})")
        print(f"    Anomaly:   {is_anomaly} (score={anom_score:.3f})")
        print(f"    Probs:     {dict(zip(rf.classes_, [round(p,3) for p in proba]))}")
    
    # ==============================
    # Report
    # ==============================
    
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("# BlackHole Beacon — Spectral Classifier v1.0\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Training Data\n\n")
        f.write(f"- Samples: {len(X_scaled)}\n")
        f.write(f"- Features: {n_features}\n")
        f.write(f"- Classes: {sorted(set(labels))}\n\n")
        f.write(f"## PCA\n\n")
        for i, v in enumerate(pca.explained_variance_ratio_):
            f.write(f"- PC{i+1}: {v:.1%}\n")
        f.write(f"\n## Top Features\n\n")
        f.write("| Feature | Importance |\n|---------|-----------|\n")
        for feat, imp in importance[:8]:
            f.write(f"| {feat} | {imp:.3f} |\n")
        f.write(f"\n## Anomalies Detected\n\n")
        for idx in anomaly_indices:
            s = spectral_db[idx]
            f.write(f"- {s['anchor']} ({s['type']}): {','.join(s.get('flags',[]))}\n")

else:
    # Simplified version without sklearn
    print("\n--- Feature Statistics (no sklearn available) ---")
    # Simple feature analysis
    for feat in ALL_FEATURES:
        vals = [v[ALL_FEATURES.index(feat)] for v in X_filled if v[ALL_FEATURES.index(feat)] is not None]
        if vals:
            vals.sort()
            print(f"  {feat:12s}: median={vals[len(vals)//2]:+.3f}")

print(f"\nReport: {REPORT}")
print("Done.")
