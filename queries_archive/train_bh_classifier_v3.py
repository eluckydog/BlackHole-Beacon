#!/usr/bin/env python3
"""
Train Black Hole vs. Pulsar classifier (v3).
Use 20 BlackCAT sources (positive) + 5+ pulsars (negative).
"""

import os
import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
import joblib

def load_training_data(
    bh_json="data/known_bh_xray_binaries_features_v2.json",
    psr_json="data/known_pulsars_features.json"
):
    """Load BlackCAT (positive) and pulsar (negative) samples with features."""
    print(f"[INFO] Loading BlackCAT: {bh_json}")
    print(f"[INFO] Loading pulsars: {psr_json}")
    
    # Load BlackCAT
    with open(bh_json, 'r', encoding='utf-8') as f:
        bh_data = json.load(f)
    
    # Load pulsars
    with open(psr_json, 'r', encoding='utf-8') as f:
        psr_data = json.load(f)
    
    # Extract features for BlackCAT (positive samples)
    X_pos = []
    y_pos = []
    bh_names = []
    
    for bh in bh_data["black_holes"]:
        if bh.get("has_features") and bh.get("features"):
            feat = bh["features"]
            # Use only 2 most stable features (J-H, H-K)
            jh = feat.get("J-H")
            hk = feat.get("H-K")
            
            if jh is not None and hk is not None:
                X_pos.append([jh, hk])
                y_pos.append(1)  # 1 = Black Hole
                bh_names.append(bh["name"])
            elif jh is not None or hk is not None:
                # Partial features - use median fill
                X_pos.append([jh if jh is not None else np.nan, hk if hk is not None else np.nan])
                y_pos.append(1)
                bh_names.append(bh["name"])
    
    # Extract features for pulsars (negative samples)
    X_neg = []
    y_neg = []
    psr_names = []
    
    for psr in psr_data["pulsars"]:
        if psr.get("has_features") and psr.get("features"):
            feat = psr["features"]
            # Use only 2 most stable features (J-H, H-K)
            jh = feat.get("J-H")
            hk = feat.get("H-K")
            
            if jh is not None or hk is not None:
                X_neg.append([
                    jh if jh is not None else np.nan,
                    hk if hk is not None else np.nan
                ])
                y_neg.append(0)  # 0 = Pulsar
                psr_names.append(psr["name"])      
    
    # Combine
    X = np.array(X_pos + X_neg)
    y = np.array(y_pos + y_neg)
    names = bh_names + psr_names
    
    print(f"[INFO] Positive samples (Black Holes): {len(X_pos)}")
    print(f"[INFO] Negative samples (Pulsars): {len(X_neg)}")
    print(f"[INFO] Total training samples: {len(X)}")
    
    if len(X_pos) < 5 or len(X_neg) < 3:
        print("[ERROR] Not enough samples! Need at least 5 positive and 3 negative.")
        return None, None, None
    
    return X, y, names

def train_random_forest(X, y):
    """Train Random Forest classifier."""
    print("\n[INFO] Training Random Forest classifier...")
    
    # Fill NaN values with median (for partial features)
    from sklearn.impute import SimpleImputer
    imputer = SimpleImputer(strategy='median')
    X_imputed = imputer.fit_transform(X)
    
    print(f"[INFO] Filled NaN values with median. Shape: {X_imputed.shape}")
    
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42,
        n_jobs=-1
    )
    
    # Cross-validation
    print("[INFO] Running 5-fold cross-validation...")
    cv_scores = cross_val_score(clf, X, y, cv=5, scoring='roc_auc')
    
    print(f"[INFO] CV AUC scores: {cv_scores}")
    print(f"[INFO] Mean AUC: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
    
    # Train on full data
    clf.fit(X, y)
    
    # Feature importance
    feature_names = ["J-H", "H-K", "W1-W2", "W2-W3"]
    importances = clf.feature_importances_
    
    print("\n[INFO] Feature importance:")
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
        print(f"  {name}: {imp:.3f}")
    
    return clf, cv_scores

def save_model(clf, output_path="data/bh_vs_psr_rf_model_v3.pkl"):
    """Save trained model."""
    print(f"\n[INFO] Saving model to: {output_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(clf, output_path)
    
    print(f"[OK] Model saved to: {output_path}")
    return output_path

def main():
    print("=" * 60)
    print("Black Hole vs. Pulsar - Training (v3)")
    print("=" * 60)
    
    # Step 1: Load training data
    X, y, names = load_training_data(
        bh_json="data/known_bh_xray_binaries_features_v2.json",
        psr_json="data/known_pulsars_features.json"
    )
    
    if X is None:
        print("[ERROR] Failed to load training data. Check JSON files.")
        return
    
    # Step 2: Train classifier
    clf, cv_scores = train_random_forest(X, y)
    
    # Step 3: Save model
    model_path = save_model(
        clf,
        output_path="data/bh_vs_psr_rf_model_v3.pkl"
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Training samples: {len(X)}")
    print(f"  - Positive (Black Holes): {sum(y == 1)}")
    print(f"  - Negative (Pulsars): {sum(y == 0)}")
    print(f"Cross-validation AUC: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
    print(f"Model saved to: {model_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
