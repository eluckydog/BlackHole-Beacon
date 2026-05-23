#!/usr/bin/env python3
"""
Predict black hole probability for v9.0 candidates using trained model (v3).
Load trained model and predict p(BH) for all candidates.
"""

import os
import json
import numpy as np
import joblib
from sklearn.impute import SimpleImputer

def load_v9_candidates(json_path="data/phase3_candidates_full.json"):
    """Load v9.0 candidates from phase3 results."""
    print(f"[INFO] Loading v9.0 candidates: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both list and dict formats
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        candidates = data.get("candidates", [])
    else:
        candidates = []
    
    print(f"[INFO] Total candidates: {len(candidates)}")
    return candidates

def extract_features(candidate):
    """Extract IR color features from candidate data."""
    features = []
    
    # Try to get IR magnitudes from candidate data
    # Structure 1: direct keys (J, H, K, W1, W2, W3)
    j_mag = candidate.get("J")
    h_mag = candidate.get("H")
    k_mag = candidate.get("K")
    w1_mag = candidate.get("W1")
    w2_mag = candidate.get("W2")
    w3_mag = candidate.get("W3")
    
    # Structure 2: nested under match_data
    if j_mag is None and "match_data" in candidate:
        match_data = candidate.get("match_data", {})
        
        # Extract 2MASS mags
        if "2mass" in match_data and match_data["2mass"]:
            mass_data = match_data["2mass"][0] if isinstance(match_data["2mass"], list) else match_data["2mass"]
            j_mag = mass_data.get("J_mag")
            h_mag = mass_data.get("H_mag")
            k_mag = mass_data.get("K_mag")
        
        # Extract WISE mags
        if "wise" in match_data and match_data["wise"]:
            wise_data = match_data["wise"][0] if isinstance(match_data["wise"], list) else match_data["wise"]
            w1_mag = wise_data.get("W1_mag")
            w2_mag = wise_data.get("W2_mag")
            w3_mag = wise_data.get("W3_mag")
    
    # Calculate colors (handle missing mags)
    jh = None
    hk = None
    w1w2 = None
    w2w3 = None
    
    if j_mag is not None and h_mag is not None:
        jh = j_mag - h_mag
    
    if h_mag is not None and k_mag is not None:
        hk = h_mag - k_mag
    
    if w1_mag is not None and w2_mag is not None:
        w1w2 = w1_mag - w2_mag
    
    if w2_mag is not None and w3_mag is not None:
        w2w3 = w2_mag - w3_mag
    
    return [jh, hk, w1w2, w2w3]

def predict_bh_probability(candidates, model_path="data/bh_vs_psr_rf_model_v3.pkl"):
    """Predict p(BH) for candidates."""
    print(f"[INFO] Loading model: {model_path}")
    
    model = joblib.load(model_path)
    print(f"[OK] Model loaded")
    
    # Extract features
    X = []
    valid_candidates = []
    
    for cand in candidates:
        feat = extract_features(cand)
        
        # Check if at least 2 features are available
        valid_count = sum(1 for f in feat if f is not None)
        
        if valid_count >= 2:
            X.append([f if f is not None else np.nan for f in feat])
            valid_candidates.append(cand)
    
    X = np.array(X)
    print(f"[INFO] Candidates with >=2 features: {len(X)}/{len(candidates)}")
    
    # Fill NaN with median
    imputer = SimpleImputer(strategy='median')
    X_imputed = imputer.fit_transform(X)
    
    # Predict probability of class 1 (Black Hole)
    proba = model.predict_proba(X_imputed)[:, 1]  # Probability of class 1
    
    # Combine with candidate info
    results = []
    for i, cand in enumerate(valid_candidates):
        result = {
            "anchor": cand.get("anchor", "Unknown"),
            "proba_bh": float(proba[i]),
            "anomaly_score": cand.get("anomaly_score"),
            "proper_motion_masyr": cand.get("proper_motion_masyr")
        }
        results.append(result)
    
    # Sort by p(BH) descending
    results.sort(key=lambda x: x["proba_bh"], reverse=True)
    
    print(f"[OK] Predictions complete. Top p(BH): {results[0]['proba_bh']:.4f}")
    return results

def save_predictions(results, output_path="data/v9_candidates_bh_probability_v3.json"):
    """Save predictions to JSON."""
    print(f"[INFO] Saving predictions: {output_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    output = {
        "metadata": {
            "model": "bh_vs_psr_rf_model_v3.pkl",
            "training_samples": 25,
            "cv_auc": "0.8750 +/- 0.1581",
            "prediction_date": "2026-05-23"
        },
        "num_candidates": len(results),
        "top_20": results[:20],
        "all_results": results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved to: {output_path}")
    return output_path

def print_top_20(results, title="Top 20 Candidates by p(BH)"):
    """Print top 20 candidates."""
    print("\n" + "="*60)
    print(title)
    print("="*60)
    print(f"{'Rank':<5} {'Anchor':<20} {'p(BH)':<10} {'Anomaly':<10} {'PM':<10}")
    print("-"*60)
    
    for i, r in enumerate(results[:20], start=1):
        print(f"{i:<5} {r['anchor']:<20} {r['proba_bh']:<10.4f} {str(r['anomaly_score'])[:9]:<10} {str(r['proper_motion_masyr'])[:9]:<10}")
    
    print("="*60)

def main():
    print("="*60)
    print("Black Hole Probability Prediction (v3)")
    print("="*60)
    
    # Step 1: Load v9.0 candidates
    candidates = load_v9_candidates(
        json_path="data/phase3_candidates_full.json"
    )
    
    if not candidates:
        print("[ERROR] No candidates loaded. Check phase3_candidates_full.json")
        return
    
    # Step 2: Predict p(BH)
    results = predict_bh_probability(
        candidates,
        model_path="data/bh_vs_psr_rf_model_v3.pkl"
    )
    
    # Step 3: Save predictions
    output_path = save_predictions(
        results,
        output_path="data/v9_candidates_bh_probability_v3.json"
    )
    
    # Step 4: Print top 20
    print_top_20(results)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Model: bh_vs_psr_rf_model_v3.pkl")
    print(f"Training samples: 25 (20 BH + 5 PSR)")
    print(f"CV AUC: 0.8750 +/- 0.1581")
    print(f"Candidates predicted: {len(results)}")
    print(f"Top p(BH): {results[0]['proba_bh']:.4f}")
    print(f"Output: {output_path}")
    print("="*60)

if __name__ == "__main__":
    main()
