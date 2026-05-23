#!/usr/bin/env python3
"""
Validate top 10 BH candidates using web_fetch (Simbad web interface).
Avoid astroquery column name issues.
"""

import os
import json
import subprocess
import re

def load_top_candidates(json_path="data/v9_candidates_ir_cut_v1.json", top_n=10):
    """Load top N candidates from IR-cut selection."""
    print(f"[INFO] Loading top {top_n} candidates: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    candidates = data.get("top_20", [])[:top_n]
    
    print(f"[INFO] Loadeed {len(candidates)} candidates")
    return candidates

def query_simbad_web(anchor_name):
    """Query Simbad using web_fetch (Simbad web interface)."""
    # Parse anchor name to RA/Dec
    # Format: JHHMM±DDMM (e.g, J1840-0643 = 18h40m, -06d43m)
    try:
        name = anchor_name[1:]  # Remove 'J' prefix
        
        # Parse RA (HHMM)
        ra_h = int(name[0:2])
        ra_m = int(name[2:4])
        ra_deg = (ra_h + ra_m / 60.0) * 15.0  # Convert HMS to degrees
        
        # Parse Dec (±DDMM)
        dec_sign = 1 if name[4] == '+' else -1
        dec_d = int(name[5:7])
        dec_m = int(name[7:9])
        dec_deg = dec_sign * (dec_d + dec_m / 60.0)
        
        print(f"[INFO]   Parsed {anchor_name} -> RA={ra_deg:.4f}, Dec={dec_deg:.4f}")
        
        # Query Simbad web interface (Coordinate query)
        simbad_url = f"http://simbad.u-strasbg.fr/simbad/sim-coo?Coord={ra_deg:+.4f}{dec_deg:+.4f}&Radius=5&Radius.unit=arcmin&submit=submit+query"
        
        # Use web_fetch
        cmd = f'python -c "import sys; from openclaw.tools import web_fetch; print(web_fetch(\'{simbad_url}\'))"'
        
        # Actually, simpler: just return the URL and let the AI use web_fetch tool
        return {
            "anchor": anchor_name,
            "ra_deg": ra_deg,
            "dec_deg": dec_deg,
            "simbad_url": simbad_url
        }
        
    except Exception as e:
        print(f"[ERROR]  Failed to parse {anchor_name}: {e}")
        return None

def validate_candidates(candidates):
    """Validate candidates (print Simbad URLs for AI to check)."""
    print(f"\n[INFO] Validating {len(candidates)} candidates...\n")
    
    results = []
    
    for i, cand in enumerate(candidates, start=1):
        anchor = cand["anchor"]
        score = cand["score"]
        colors = cand.get("colors", {})
        pm = cand.get("proper_motion_masyr")
        
        print(f"[{i:2d}/10] {anchor} (score={score:.3f})")
        
        # Get Simbad URL
        info = query_simbad_web(anchor)
        
        if info:
            print(f"       Simbad URL: {info['simbad_url']}")
            print(f"       (AI: use web_fetch to check this URL)")
        else:
            print(f"       Failed to parse {anchor}")
        
        result = {
            "rank": i,
            "anchor": anchor,
            "score": score,
            "colors": colors,
            "proper_motion_masyr": pm,
            "simbad_url": info["simbad_url"] if info else None,
            "validation_status": "pending"  # AI will update this after web_fetch
        }
        
        results.append(result)
        print()
    
    return results

def save_validation(results, output_path="data/validation_bh_ir_cut_v2.json"):
    """Save validation results to JSON."""
    print(f"[INFO] Saving validation: {output_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    output = {
        "metadata": {
            "method": "IR color-cut + Simbad web (web_fetch)",
            "num_candidates": len(results),
            "validation_date": "2026-05-23",
            "note": "AI should use web_fetch to check each simbad_url"
        },
        "results": results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved to: {output_path}")
    return output_path

def print_top_10(results):
    """Print top 10 candidates (for AI to validate)."""
    print("\n" + "="*60)
    print("Top 10 Candidates for Validation")
    print("="*60)
    print(f"{'Rank':<5} {'Anchor':<20} {'Score':<10} {'Simbad URL':<50}")
    print("-"*60)
    
    for r in results[:10]:
        url = r.get('simbad_url', 'N/A')
        url_short = url[:47] + "..." if len(url) > 50 else url
        
        print(f"{r['rank']:<5} {r['anchor']:<20} {r['score']:<10.3f} {url_short:<50}")
    
    print("="*60)
    print("\nAI: Use web_fetch to check each Simbad URL.")
    print("Look for: otype = 'BH*', 'X', 'LMXB', 'IMXB' (black hole candidates).")
    print("If not known -> possibly NEW discovery!")

def main():
    print("="*60)
    print("Black Hole Candidate Validation (v2 - web_fetch)")
    print("="*60)
    
    # Step 1: Load top 10 candidates
    candidates = load_top_candidates(
        json_path="data/v9_candidates_ir_cut_v1.json",
        top_n=10
    )
    
    if not candidates:
        print("[ERROR] No candidates loaded. Check v9_candidates_ir_cut_v1.json")
        return
    
    # Step 2: Validate (generate Simbad URLs)
    results = validate_candidates(candidates)
    
    # Step 3: Save validation
    output_path = save_validation(
        results,
        output_path="data/validation_bh_ir_cut_v2.json"
    )
    
    # Step 4: Print top 10 (for AI to validate)
    print_top_10(results)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Candidates validated: {len(results)}")
    print(f"Method: IR color-cut + Simbad web (web_fetch)")
    print(f"Output: {output_path}")
    print("\nNext step: AI uses web_fetch to check each Simbad URL.")
    print("="*60)

if __name__ == "__main__":
    main()
