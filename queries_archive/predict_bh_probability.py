"""
predict_bh_probability.py - Predict black hole probability for v9.0 candidates
====================================================================================
Compute IR colors from raw magnitudes, then apply trained RF model.

Author: math-science workspace / BlackHole Beacon project
Date: 2026-05-23
"""

import json
import numpy as np
import joblib
from pathlib import Path

def predict_bh_probability():
    # --- 1. Load trained model ---
    model_path = Path(__file__).parent.parent / "data" / "bh_vs_psr_rf_model_v2.pkl"
    
    try:
        clf = joblib.load(model_path)
        print(f"[OK] Loaded model from: {model_path}")
    except FileNotFoundError:
        print(f"[ERROR] Model not found: {model_path}")
        print("  Run train_bh_classifier_v2.py first!")
        return None
    
    # --- 2. Load v9.0 candidates ---
    candidates_path = Path(__file__).parent.parent / "data" / "phase3_candidates_full.json"
    
    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    
    print(f"[INFO] Loaded {len(candidates)} candidates")
    
    # --- 3. Compute IR colors for each candidate ---
    feature_names = ["J-H", "H-K", "W1-W2", "W2-W3"]
    X = []
    valid_indices = []
    
    for i, cand in enumerate(candidates):
        # Compute IR colors
        J = cand.get("J")
        H = cand.get("H")
        K = cand.get("K")
        W1 = cand.get("W1")
        W2 = cand.get("W2")
        W3 = cand.get("W3")  # Might not exist
        
        # Compute colors
        JH = J - H if J is not None and H is not None else np.nan
        HK = H - K if H is not None and K is not None else np.nan
        W1W2 = W1 - W2 if W1 is not None and W2 is not None else np.nan
        W2W3 = W2 - W3 if W2 is not None and W3 is not None else np.nan
        
        features = [JH, HK, W1W2, W2W3]
        
        # Skip if all features are NaN
        if all(np.isnan(features)):
            continue
        
        X.append(features)
        valid_indices.append(i)
    
    if len(X) == 0:
        print("[ERROR] No candidates with valid IR colors")
        return None
    
    X = np.array(X)
    
    # Handle NaN: replace with mean of column
    for i in range(X.shape[1]):
        col = X[:, i]
        mask = ~np.isnan(col)
        if mask.sum() > 0:
            mean_val = col[mask].mean()
            X[~mask, i] = mean_val
    
    print(f"[INFO] Predicting for {len(X)} candidates (with valid IR colors)")
    
    # --- 4. Predict black hole probability ---
    probs = clf.predict_proba(X)[:, 1]  # Probability of class 1 (black hole)
    
    # --- 5. Rank candidates by probability ---
    results = []
    for idx, prob in zip(valid_indices, probs):
        cand = candidates[idx]
        results.append({
            "rank": len(results) + 1,
            "anchor": cand.get("anchor"),
            "designation": cand.get("designation"),
            "p_bh": float(prob),
            "anomaly_score": cand.get("anomaly_score", None),
            "prob_v9": cand.get("prob", None),
            "score_total": cand.get("scores", {}).get("total", None) if isinstance(cand.get("scores"), dict) else None,
            "pm_total": cand.get("proper_motion_masyr")
        })
    
    # Sort by p_bh (descending)
    results.sort(key=lambda x: x["p_bh"], reverse=True)
    
    # Re-rank
    for i, r in enumerate(results):
        r["rank"] = i + 1
    
    # --- 6. Save results ---
    output_path = Path(__file__).parent.parent / "data" / "v9_candidates_bh_probability.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Saved predictions to: {output_path}")
    print(f"\n[INFO] TOP 10 black hole candidates (by p_bh):")
    for r in results[:10]:
        print(f"  {r['rank']}. {r['anchor']}: p(BH) = {r['p_bh']:.3f}")
    
    return results

if __name__ == "__main__":
    predict_bh_probability()
