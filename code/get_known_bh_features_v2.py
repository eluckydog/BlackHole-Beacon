"""
get_known_bh_features_v2.py - Get IR colors + PM for known black holes (fixed)
============================================================================================
Fix: load correct JSON file (with Simbad coordinates)

Author: math-science workspace / BlackHole Beacon project
Date: 2026-05-23
"""

import json
import time
from pathlib import Path

try:
    from astroquery.vizier import Vizier
    from astroquery.gaia import Gaia
    HAS_ASTROQUERY = True
except ImportError:
    HAS_ASTROQUERY = False
    print("[WARN] astroquery not installed. Install: pip install astroquery")

# Vizier table IDs
TABLE_2MASS = "II/246/out"
TABLE_WISE = "II/328/allwise"
TABLE_GAIA = "I/355/gaiadr3"

def get_known_bh_features_v2():
    if not HAS_ASTROQUERY:
        print("[ERROR] astroquery not available.")
        return None
    
    # Load known BH list (WITH Simbad coordinates)
    input_path = Path(__file__).parent.parent / "data" / "known_bh_xray_binaries_simbad_v3.json"
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"[INFO] Loaded {len(data['black_holes'])} known black holes (with Simbad coords)")
    
    # For each BH, cross-match with 2MASS, WISE, Gaia
    updated_bh = []
    
    for i, bh in enumerate(data["black_holes"]):
        name = bh.get("simbad_main_id", bh["name"])
        ra = bh.get("simbad_ra_deg")
        dec = bh.get("simbad_dec_deg")
        
        if ra is None or dec is None:
            print(f"[{i+1}/{len(data['black_holes'])}] SKIP (no Simbad coords): {name}")
            bh["features"] = {}
            bh["has_features"] = False
            updated_bh.append(bh)
            continue
        
        print(f"[{i+1}/{len(data['black_holes'])}] Cross-matching: {name}...")
        
        # Initialize features
        features = {
            "J_mag": None, "H_mag": None, "K_mag": None,
            "W1_mag": None, "W2_mag": None, "W3_mag": None,
            "pm_ra": None, "pm_dec": None, "pm_total": None,
        }
        
        # --- 1. Query 2MASS (J, H, K) ---
        try:
            Vizier.ROW_LIMIT = -1  # no limit
            result_2mass = Vizier.query_region(f"{ra} {dec}", radius="5s", catalog=TABLE_2MASS)
            
            if result_2mass is not None and len(result_2mass) > 0:
                # Take closest match (first row)
                t = result_2mass[0]
                features["J_mag"] = float(t["Jmag"][0]) if "Jmag" in t.colnames else None
                features["H_mag"] = float(t["Hmag"][0]) if "Hmag" in t.colnames else None
                features["K_mag"] = float(t["Kmag"][0]) if "Kmag" in t.colnames else None
                
                print(f"  [OK] 2MASS: J={features['J_mag']:.2f}, H={features['H_mag']:.2f}, K={features['K_mag']:.2f}")
        except Exception as e:
            print(f"  [WARN] 2MASS query failed: {e}")
        
        # --- 2. Query WISE (W1, W2, W3) ---
        try:
            result_wise = Vizier.query_region(f"{ra} {dec}", radius="5s", catalog=TABLE_WISE)
            
            if result_wise is not None and len(result_wise) > 0:
                t = result_wise[0]
                features["W1_mag"] = float(t["W1mag"][0]) if "W1mag" in t.colnames else None
                features["W2_mag"] = float(t["W2mag"][0]) if "W2mag" in t.colnames else None
                features["W3_mag"] = float(t["W3mag"][0]) if "W3mag" in t.colnames else None
                
                print(f"  [OK] WISE: W1={features['W1_mag']:.2f}, W2={features['W2_mag']:.2f}, W3={features['W3_mag']:.2f}")
        except Exception as e:
            print(f"  [WARN] WISE query failed: {e}")
        
        # --- 3. Query Gaia (PM) ---
        try:
            result_gaia = Vizier.query_region(f"{ra} {dec}", radius="5s", catalog=TABLE_GAIA)
            
            if result_gaia is not None and len(result_gaia) > 0:
                t = result_gaia[0]
                pmra = float(t["pmra"][0]) if "pmra" in t.colnames else None
                pmdec = float(t["pmdec"][0]) if "pmdec" in t.colnames else None
                
                features["pm_ra"] = pmra
                features["pm_dec"] = pmdec
                features["pm_total"] = (pmra**2 + pmdec**2)**0.5 if pmra is not None and pmdec is not None else None
                
                print(f"  [OK] Gaia: pmra={pmra:.1f}, pmdec={pmdec:.1f}, pm_total={features['pm_total']:.1f}")
        except Exception as e:
            print(f"  [WARN] Gaia query failed: {e}")
        
        # Compute IR colors
        if features["J_mag"] is not None and features["H_mag"] is not None:
            features["J-H"] = features["J_mag"] - features["H_mag"]
        if features["H_mag"] is not None and features["K_mag"] is not None:
            features["H-K"] = features["H_mag"] - features["K_mag"]
        if features["W1_mag"] is not None and features["W2_mag"] is not None:
            features["W1-W2"] = features["W1_mag"] - features["W2_mag"]
        if features["W2_mag"] is not None and features["W3_mag"] is not None:
            features["W2-W3"] = features["W2_mag"] - features["W3_mag"]
        
        # Add features to bh record
        bh["features"] = features
        bh["has_features"] = any(v is not None for k, v in features.items() if k not in ["J-H", "H-K", "W1-W2", "W2-W3"])
        
        updated_bh.append(bh)
        
        # Rate limiting
        time.sleep(1.0)  # 1 second between queries
    
    # Save updated data
    output_path = Path(__file__).parent.parent / "data" / "known_bh_xray_binaries_features_v2.json"
    data["black_holes"] = updated_bh
    data["metadata"]["feature_query_date"] = time.strftime("%Y-%m-%d")
    data["metadata"]["feature_query_status"] = f"{sum(1 for bh in updated_bh if bh.get('has_features', False))}/{len(updated_bh)} with features"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Saved updated data to: {output_path}")
    print(f"[STATS] With features: {sum(1 for bh in updated_bh if bh.get('has_features', False))}/{len(updated_bh)}")
    return output_path

if __name__ == "__main__":
    get_known_bh_features_v2()
