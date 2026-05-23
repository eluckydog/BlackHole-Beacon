#!/usr/bin/env python3
"""
Simple IR color-cut based black hole candidate selection.
No machine learning - just physics-based cuts.
"""

import os
import json

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

def calculate_ir_colors(candidate):
    """Calculate IR colors from candidate data."""
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
    colors = {}
    
    if j_mag is not None and h_mag is not None:
        colors["J-H"] = j_mag - h_mag
    
    if h_mag is not None and k_mag is not None:
        colors["H-K"] = h_mag - k_mag
    
    if w1_mag is not None and w2_mag is not None:
        colors["W1-W2"] = w1_mag - w2_mag
    
    if w2_mag is not None and w3_mag is not None:
        colors["W2-W3"] = w2_mag - w3_mag
    
    return colors

def black_hole_score(candidate):
    """
    Calculate "black-hole-ness" score based on IR colors and proper motion.
    
    Black hole X-ray binaries have:
    1. Red IR colors (accretion disk) -> W1-W2 > 0.3, W2-W3 > 0.5
    2. No proper motion (or very small) -> PM < 10 mas/yr
    3. X-ray source (but we don't have X-ray data)
    
    Score = sum of (color - threshold) for red colors + PM penalty
    Higher = more likely black hole
    """
    colors = calculate_ir_colors(candidate)
    
    score = 0.0
    
    # IR color cuts (red = accretion disk)
    if "W1-W2" in colors:
        w1w2 = colors["W1-W2"]
        if w1w2 > 0.3:  # Red in WISE
            score += (w1w2 - 0.3) * 2.0  # Weight
    
    if "W2-W3" in colors:
        w2w3 = colors["W2-W3"]
        if w2w3 > 0.5:  # Red in mid-IR
            score += (w2w3 - 0.5) * 1.5
    
    if "J-H" in colors:
        jh = colors["J-H"]
        if jh > 0.5:  # Red in 2MASS
            score += (jh - 0.5) * 1.0
    
    if "H-K" in colors:
        hk = colors["H-K"]
        if hk > 0.3:  # Red in 2MASS
            score += (hk - 0.3) * 1.0
    
    # Proper motion penalty (black holes have small PM)
    pm = candidate.get("proper_motion_masyr")
    if pm is not None and pm > 0:
        if pm > 100:  # Large PM = pulsar or star
            score -= 5.0  # Strong penalty
        elif pm > 10:  # Medium PM = possibly pulsar
            score -= 1.0  # Mild penalty
        # else: small PM = good, no penalty
    
    return score, colors

def select_bh_candidates(candidates, top_n=20):
    """Select black hole candidates using IR color cuts."""
    print(f"\n[INFO] Scoring {len(candidates)} candidates...")
    
    scored = []
    
    for cand in candidates:
        score, colors = black_hole_score(cand)
        
        # Only keep candidates with at least 1 IR color
        if len(colors) >= 1:
            result = {
                "anchor": cand.get("anchor", "Unknown"),
                "score": score,
                "colors": colors,
                "proper_motion_masyr": cand.get("proper_motion_masyr"),
                "anomaly_score": cand.get("anomaly_score")
            }
            scored.append(result)
    
    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    print(f"[OK] Scored {len(scored)} candidates")
    print(f"[INFO] Top score: {scored[0]['score']:.4f}")
    print(f"[INFO] Top candidate: {scored[0]['anchor']}")
    
    return scored[:top_n]

def save_candidates(candidates, output_path="data/v9_candidates_ir_cut_v1.json"):
    """Save selected candidates to JSON."""
    print(f"\n[INFO] Saving candidates: {output_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    output = {
        "metadata": {
            "method": "IR color-cut (no machine learning)",
            "criteria": {
                "W1-W2 > 0.3": "Red in WISE (accretion disk)",
                "W2-W3 > 0.5": "Red in mid-IR",
                "PM < 10 mas/yr": "Small proper motion (black hole)",
                "PM > 100 mas/yr penalty": "Large PM = pulsar/star"
            },
            "selection_date": "2026-05-23"
        },
        "num_candidates": len(candidates),
        "top_20": candidates[:20],
        "all_results": candidates
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved to: {output_path}")
    return output_path

def print_top_20(candidates, title="Top 20 Black Hole Candidates (IR Color-Cut)"):
    """Print top 20 candidates."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(f"{'Rank':<5} {'Anchor':<20} {'Score':<10} {'W1-W2':<10} {'PM':<10}")
    print("-" * 60)
    
    for i, r in enumerate(candidates[:20], start=1):
        w1w2 = r['colors'].get('W1-W2', 'N/A')
        w1w2_str = f"{w1w2:.3f}" if isinstance(w1w2, float) else w1w2
        
        print(f"{i:<5} {r['anchor']:<20} {r['score']:<10.4f} {w1w2_str:<10} {str(r['proper_motion_masyr'])[:9]:<10}")
    
    print("=" * 60)

def main():
    print("=" * 60)
    print("Black Hole Candidate Selection - IR Color-Cut (v1)")
    print("=" * 60)
    
    # Step 1: Load v9.0 candidates
    candidates = load_v9_candidates(
        json_path="data/phase3_candidates_full.json"
    )
    
    if not candidates:
        print("[ERROR] No candidates loaded. Check phase3_candidates_full.json")
        return
    
    # Step 2: Select candidates using IR color cuts
    top_candidates = select_bh_candidates(
        candidates,
        top_n=20
    )
    
    # Step 3: Save candidates
    output_path = save_candidates(
        top_candidates,
        output_path="data/v9_candidates_ir_cut_v1.json"
    )
    
    # Step 4: Print top 20
    print_top_20(top_candidates)
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Method: IR color-cut (no machine learning)")
    print(f"Criteria:")
    print(f"  - W1-W2 > 0.3 (red in WISE)")
    print(f"  - W2-W3 > 0.5 (red in mid-IR)")
    print(f"  - PM < 10 mas/yr (small proper motion)")
    print(f"Top score: {top_candidates[0]['score']:.4f}")
    print(f"Top candidate: {top_candidates[0]['anchor']}")
    print(f"Output: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
