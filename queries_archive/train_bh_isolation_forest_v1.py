#!/usr/bin/env python3
"""
Train Isolation Forest on BlackCAT sources (unsupervised).
Learn IR color distribution of known black holes.
Then predict v9.0 candidates (anomaly score = how "black-hole-like").
"""

import os
import json
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
import joblib

def load_blackcat_features(json_path="data/known_bh_xray_binaries_features_v2.json"):
    """Load BlackCAT sources with IR color features."""
    print(f"[INFO] Loading BlackCAT: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract features (accept partial, fill with median)
    X = []
    names = []
    
    for bh in data["black_holes"]:
        if bh.get("has_features") and bh.get("features"):
            feat = bh["features"]
            
            # Get 4 IR color features
            jh = feat.get("J-H")
            hk = feat.get("H-K")
            w1w2 = feat.get("W1-W2")
            w2w3 = feat.get("W2-W3")
            
            # Count available features
            available = sum(1 for v in [jh, hk, w1w2, w2w3] if v is not None)
            
            if available >= 2:  # At least 2 features
                X.append([
                    jh if jh is not None else np.nan,
                    hk if hk is not None else np.nan,
                    w1w2 if w1w2 is not None else np.nan,
                    w2w3 if w2w3 is not None else np.nan
                ])
                names.append(bh["name"])
    
    X = np.array(X)
    print(f"[INFO] BlackCAT samples with >=2 features: {len(X)}/{len(data['black_holes'])}")
    
    return X, names

def train_isolation_forest(X, contamination=0.1):
    """Train Isolation Forest on BlackCAT IR colors."""
    print(f"\n[INFO] Training Isolation Forest (contamination={contamination})...")
    
    # Fill NaN with median
    imputer = SimpleImputer(strategy='median')
    X_imputed = imputer.fit_transform(X)
    
    print(f"[INFO] Filled NaN values. Shape: {X_imputed.shape}")
    
    # Train Isolation Forest
    clf = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    
    clf.fit(X_imputed)
    
    print(f"[OK] Isolation Forest trained on {len(X)} BlackCAT sources")
    
    # Print anomaly score statistics
    scores = clf.score_samples(X_imputed)
    print(f"[INFO] Anomaly score range: [{scores.min():.4f}, {scores.max():.4f}]")
    print(f"[INFO] Anomaly score mean: {scores.mean():.4f}")
    
    return clf, imputer

def save_model(clf, imputer, output_path="data/bh_isolation_forest_v1.pkl"):
    """Save trained model and imputer."""
    print(f"\n[INFO] Saving model: {output_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save both classifier and imputer
    joblib.dump({
        "classifier": clf,
        "imputer": imputer
    }, output_path)
    
    print(f"[OK] Model saved to: {output_path}")
    return output_path

def main():
    print("=" * 60)
    print("Black Hole - Isolation Forest Training (v1)")
    print("=" * 60)
    
    # Step 1: Load BlackCAT features
    X, names = load_blackcat_features(
        json_path="data/known_bh_xray_binaries_features_v2.json"
    )
    
    if len(X) < 10:
        print("[ERROR] Not enough samples! Need at least 10.")
        return
    
    # Step 2: Train Isolation Forest
    clf, imputer = train_isolation_forest(
        X,
        contamination=0.1  # Assume 10% of BlackCAT are "outliers" (unusual IR colors)
    )
    
    # Step 3: Save model
    model_path = save_model(
        clf, imputer,
        output_path="data/bh_isolation_forest_v1.pkl"
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Training samples: {len(X)} (BlackCAT sources)")
    print(f"Features: 4 IR colors (J-H, H-K, W1-W2, W2-W3)")
    print(f"Contamination: 0.1 (10% outliers)")
    print(f"Model saved to: {model_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
