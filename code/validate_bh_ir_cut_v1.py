#!/usr/bin/env python3
"""
Validate top 10 BH candidates using Simbad.
Check if known BH/X-ray source, or new discovery.
"""

import os
import json
from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord
from astropy import units as u

def load_top_candidates(json_path="data/v9_candidates_ir_cut_v1.json", top_n=10):
    """Load top N candidates from IR-cut selection."""
    print(f"[INFO] Loading top {top_n} candidates: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    candidates = data.get("top_20", [])[:top_n]
    
    print(f"[INFO] Loaded {len(candidates)} candidates")
    return candidates

def query_simbad(anchor_name):
    """Query Simbad for a candidate by anchor name (e.g, 'J1840-0643')."""
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
        
        # Query Simbad
        coord = SkyCoord(ra_deg, dec_deg, unit='deg', frame='icrs')
        result = Simbad.query_region(coord, radius=5 * u.arcmin)
        
        if result and len(result) > 0:
            # Return top 3 matches
            matches = []
            for row in result[:3]:
                matches.append({
                    "main_id": row['MAIN_ID'],
                    "otype": row['OTYPE'],
                    "ra_deg": float(row['RA_d']) if row['RA_d'] else None,
                    "dec_deg": float(row['DEC_d']) if row['DEC_d'] else None
                })
            return matches
        
    except Exception as e:
        print(f"[ERROR]  Failed to query {anchor_name}: {e}")
        return None
    
    return None

def validate_candidates(candidates):
    """Validate candidates against Simbad."""
    print(f"\n[INFO] Validating {len(candidates)} candidates...\n")
    
    results = []
    
    for i, cand in enumerate(candidates, start=1):
        anchor = cand["anchor"]
        score = cand["score"]
        colors = cand.get("colors", {})
        pm = cand.get("proper_motion_masyr")
        
        print(f"[{i:2d}/10] {anchor} (score={score:.3f})")
        
        # Query Simbad
        matches = query_simbad(anchor)
        
        result = {
            "rank": i,
            "anchor": anchor,
            "score": score,
            "colors": colors,
            "proper_motion_masyr": pm,
            "simbad_matches": matches,
            "is_known_bh": False,
            "is_known_psr": False,
            "is_known_xray": False,
            "is_new": False
        }
        
        # Check match types
        if matches:
            for m in matches:
                otype = m.get("otype", "")
                if "BH" in otype:
                    result["is_known_bh"] = True
                if "Psr" in otype:
                    result["is_known_psr"] = True
                if "X" in otype:
                    result["is_known_xray"] = True
            
            # If not known BH/PSR/X-ray -> possibly new
            if not result["is_known_bh"] and not result["is_known_psr"] and not result["is_known_xray"]:
                result["is_new"] = True
        else:
            # No Simbad match -> possibly new!
            result["is_new"] = True
        
        results.append(result)
        
        # Print summary
        if matches:
            print(f"       Simbad: {len(matches)} match(es)")
            for m in matches[:1]:  # Show top 1
                print(f"         - {m['main_id']} [{m['otype']}]")
        else:
            print(f"       Simbad: No match (possibly NEW!)")
        
        print()
    
    return results

def save_validation(results, output_path="data/validation_bh_ir_cut_v1.json"):
    """Save validation results to JSON."""
    print(f"[INFO] Saving validation: {output_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    output = {
        "metadata": {
            "method": "IR color-cut + Simbad validation",
            "num_candidates": len(results),
            "validation_date": "2026-05-23"
        },
        "results": results,
        "summary": {
            "known_bh": sum(1 for r in results if r["is_known_bh"]),
            "known_psr": sum(1 for r in results if r["is_known_psr"]),
            "known_xray": sum(1 for r in results if r["is_known_xray"]),
            "possibly_new": sum(1 for r in results if r["is_new"])
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved to: {output_path}")
    return output_path

def print_summary(results):
    """Print validation summary."""
    print("\n" + "="*60)
    print("Validation Summary")
    print("="*60)
    
    summary = {
        "known_bh": sum(1 for r in results if r["is_known_bh"]),
        "known_psr": sum(1 for r in results if r["is_known_psr"]),
        "known_xray": sum(1 for r in results if r["is_known_xray"]),
        "possibly_new": sum(1 for r in results if r["is_new"])
    }
    
    print(f"Total candidates: {len(results)}")
    print(f"Known black holes: {summary['known_bh']}")
    print(f"Known pulsars: {summary['known_psr']}")
    print(f"Known X-ray sources: {summary['known_xray']}")
    print(f"Possibly NEW: {summary['possibly_new']}")
    
    if summary["possibly_new"] > 0:
        print("\n⭐ Possibly NEW candidates:")
        for r in results:
            if r["is_new"]:
                print(f"  #{r['rank']:2d} {r['anchor']} (score={r['score']:.3f})")
    
    print("="*60)

def main():
    print("="*60)
    print("Black Hole Candidate Validation (v1)")
    print("="*60)
    
    # Step 1: Load top 10 candidates
    candidates = load_top_candidates(
        json_path="data/v9_candidates_ir_cut_v1.json",
        top_n=10
    )
    
    if not candidates:
        print("[ERROR] No candidates loaded. Check v9_candidates_ir_cut_v1.json")
        return
    
    # Step 2: Validate against Simbad
    results = validate_candidates(candidates)
    
    # Step 3: Save validation
    output_path = save_validation(
        results,
        output_path="data/validation_bh_ir_cut_v1.json"
    )
    
    # Step 4: Print summary
    print_summary(results)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Candidates validated: {len(results)}")
    print(f"Known black holes: {sum(1 for r in results if r['is_known_bh'])}")
    print(f"Known pulsars: {sum(1 for r in results if r['is_known_psr'])}")
    print(f"Known X-ray: {sum(1 for r in results if r['is_known_xray'])}")
    print(f"Possibly NEW: {sum(1 for r in results if r['is_new'])}")
    print(f"Output: {output_path}")
    print("="*60)

if __name__ == "__main__":
    main()
