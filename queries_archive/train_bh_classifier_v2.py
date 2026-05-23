"""
train_bh_classifier_v2.py - Train black hole vs. pulsar classifier (fixed)
====================================================================================
Fix: use 'import joblib' instead of 'from sklearn.externals import joblib'

Author: math-science workspace / BlackHole Beacon project
Date: 2026-05-23
"""

import json
import numpy as np
import joblib  # Direct import (sklearn.externals deprecated)
from pathlib import Path

def train_bh_classifier_v2():
    # --- 1. Load positive samples (black holes) ---
    bh_path = Path(__file__).parent.parent / "data" / "known_bh_xray_binaries_features_v2.json"
    with open(bh_path, "r", encoding="utf-8") as f:
        bh_data = json.load(f)
    
    # --- 2. Load negative samples (pulsars) ---
    psr_path = Path(__file__).parent.parent / "data" / "known_pulsars_features.json"
    with open(psr_path, "r", encoding="utf-8") as f:
        psr_data = json.load(f)
    
    # --- 3. Extract features ---
    X_pos = []
    X_neg = []
    
    # Positive samples (black holes)
    for bh in bh_data["black_holes"]:
        if not bh.get("has_features", False):
            continue
        
        feat = bh["features"]
        # Use IR colors only (PM is None anyway)
        features = []
        for key in ["J-H", "H-K", "W1-W2", "W2-W3"]:
            val = feat.get(key)
            if val is not None:
                features.append(val)
            else:
                features.append(np.nan)
        
        # Skip if all features are NaN
        if all(np.isnan(features)):
            continue
        
        X_pos.append(features)
    
    # Negative samples (pulsars)
    for psr in psr_data["pulsars"]:
        if not psr.get("has_features", False):
            continue
        
        feat = psr["features"]
        features = []
        for key in ["J-H", "H-K", "W1-W2", "W2-W3"]:
            val = feat.get(key)
            if val is not None:
                features.append(val)
            else:
                features.append(np.nan)
        
        # Skip if all features are NaN
        if all(np.isnan(features)):
            continue
        
        X_neg.append(features)
    
    print(f"[INFO] Positive samples (BH): {len(X_pos)}")
    print(f"[INFO] Negative samples (PSR): {len(X_neg)}")
    
    if len(X_pos) == 0 or len(X_neg) == 0:
        print("[ERROR] Need at least 1 positive and 1 negative sample")
        return None
    
    # --- 4. Prepare training data ---
    X = np.array(X_pos + X_neg)
    y = np.array([1] * len(X_pos) + [0] * len(X_neg))  # 1=BH, 0=PSR
    
    # Handle NaN: replace with mean of column
    for i in range(X.shape[1]):
        col = X[:, i]
        mask = ~np.isnan(col)
        if mask.sum() > 0:
            mean_val = col[mask].mean()
            X[~mask, i] = mean_val
    
    print(f"[INFO] Training data shape: {X.shape}")
    print(f"[INFO] Labels: {y.sum()}/{len(y)} positive")
    
    # --- 5. Train classifier (Random Forest) ---
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=3,  # Strong regularization (only 16 samples!)
            random_state=42
        )
        
        # Cross-validation (5-fold, but we have only 16 samples)
        scores = cross_val_score(clf, X, y, cv=min(5, len(X)))
        print(f"[INFO] Cross-validation accuracy: {scores.mean():.2f} (+/- {scores.std():.2f})")
        
        # Train on full data
        clf.fit(X, y)
        
        # Feature importance
        feature_names = ["J-H", "H-K", "W1-W2", "W2-W3"]
        importances = clf.feature_importances_
        print("\n[INFO] Feature importances:")
        for name, imp in zip(feature_names, importances):
            print(f"  {name}: {imp:.3f}")
        
        # --- 6. Save model ---
        model_path = Path(__file__).parent.parent / "data" / "bh_vs_psr_rf_model_v2.pkl"
        joblib.dump(clf, model_path)
        print(f"\n[OK] Saved model to: {model_path}")
        
        # --- 7. Apply to v9.0 candidates (if available) ---
        apply_to_candidates(clf, feature_names)
        
        return clf, X, y
        
    except ImportError:
        print("[WARN] scikit-learn not installed. Install: pip install scikit-learn")
        return None

def apply_to_candidates(clf, feature_names):
    """
    Apply trained model to v9.0 candidates to get 'black hole probability'
    """
    candidates_path = Path(__file__).parent.parent / "data" / "top10_v9.json"
    
    if not candidates_path.exists():
        print("\n[WARN] top10_v9.json not found, skipping candidate prediction")
        return
    
    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    
    print(f"\n[INFO] Predicting black hole probability for {len(candidates)} v9.0 candidates...")
    
    # Extract features for each candidate
    X_cand = []
    valid_candidates = []
    
    for cand in candidates:
        feat = cand.get("features", {})
        features = []
        for key in feature_names:
            val = feat.get(key)
            if val is not None:
                features.append(val)
            else:
                features.append(np.nan)
        
        if all(np.isnan(features)):
            continue
        
        X_cand.append(features)
        valid_candidates.append(cand)
    
    if len(X_cand) == 0:
        print("[WARN] No candidates with valid features")
        return
    
    X_cand = np.array(X_cand)
    
    # Handle NaN
    for i in range(X_cand.shape[1]):
        col = X_cand[:, i]
        mask = ~np.isnan(col)
        if mask.sum() > 0:
            mean_val = col[mask].mean()
            X_cand[~mask, i] = mean_val
    
    # Predict probability
    probs = clf.predict_proba(X_cand)[:, 1]  # Probability of class 1 (black hole)
    
    # Print results
    print("\n[INFO] Black hole probability (v9.0 candidates):")
    for cand, prob in zip(valid_candidates, probs):
        name = cand.get("name", "Unknown")
        print(f"  {name}: p(BH) = {prob:.3f}")
    
    # Save results
    results = []
    for cand, prob in zip(valid_candidates, probs):
        results.append({
            "name": cand.get("name", "Unknown"),
            "p_bh": float(prob),
            "features": cand.get("features", {})
        })
    
    output_path = Path(__file__).parent.parent / "data" / "v9_candidates_bh_probability.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Saved predictions to: {output_path}")

if __name__ == "__main__":
    train_bh_classifier_v2()
