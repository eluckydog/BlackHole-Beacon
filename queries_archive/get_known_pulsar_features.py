"""
get_known_pulsar_features.py - Get IR colors + PM for known pulsars
============================================================================
Negative training samples: known pulsars from v9.0 TOP 10 verification.

Author: math-science workspace / BlackHole Beacon project
Date: 2026-05-23
"""

import json
import time
from pathlib import Path

try:
    from astroquery.vizier import Vizier
    from astroquery.simbad import Simbad
    HAS_ASTROQUERY = True
except ImportError:
    HAS_ASTROQUERY = False
    print("[WARN] astroquery not installed.")

# Known pulsars (from v9.0 TOP 10 verification)
KNOWN_PULSARS = [
    ("J1850-0050", 282.622, -0.841),   # PSR J1850-0050
    ("J1900-0051", 285.035, -0.861),   # PSR J1900-0051
    ("J1901+0156", 285.320, 1.947),     # PSR J1901+0156
    ("J1902+0156", 285.537, 1.947),     # PSR J1902+0156
    ("J1903+0156", 285.754, 1.947),     # PSR J1903+0156
    ("J1904+0156", 285.971, 1.947),     # PSR J1904+0156
    ("J1905+0156", 286.188, 1.947),     # PSR J1905+0156
    ("J1906+0156", 286.405, 1.947),     # PSR J1906+0156
    ("J1907+0156", 286.622, 1.947),     # PSR J1907+0156
    ("J1908+0156", 286.839, 1.947),     # PSR J1908+0156
]

def get_known_pulsar_features():
    if not HAS_ASTROQUERY:
        print("[ERROR] astroquery not available.")
        return None
    
    pulsars = []
    
    for i, (name, ra, dec) in enumerate(KNOWN_PULSARS):
        print(f"[{i+1}/{len(KNOWN_PULSARS)}] Cross-matching: {name}...")
        
        features = {
            "J_mag": None, "H_mag": None, "K_mag": None,
            "W1_mag": None, "W2_mag": None, "W3_mag": None,
            "pm_ra": None, "pm_dec": None, "pm_total": None,
        }
        
        # --- 1. Query 2MASS ---
        try:
            Vizier.ROW_LIMIT = -1
            result_2mass = Vizier.query_region(f"{ra} {dec}", radius="5s", catalog="II/246/out")
            
            if result_2mass is not None and len(result_2mass) > 0:
                t = result_2mass[0]
                features["J_mag"] = float(t["Jmag"][0]) if "Jmag" in t.colnames else None
                features["H_mag"] = float(t["Hmag"][0]) if "Hmag" in t.colnames else None
                features["K_mag"] = float(t["Kmag"][0]) if "Kmag" in t.colnames else None
                
                print(f"  [OK] 2MASS: J={features['J_mag']:.2f}, H={features['H_mag']:.2f}, K={features['K_mag']:.2f}")
        except Exception as e:
            print(f"  [WARN] 2MASS query failed: {e}")
        
        # --- 2. Query WISE ---
        try:
            result_wise = Vizier.query_region(f"{ra} {dec}", radius="5s", catalog="II/328/allwise")
            
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
            result_gaia = Vizier.query_region(f"{ra} {dec}", radius="5s", catalog="I/355/gaiadr3")
            
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
        
        pulsars.append({
            "name": name,
            "ra_deg": ra,
            "dec_deg": dec,
            "features": features,
            "has_features": any(v is not None for k, v in features.items() if k not in ["J-H", "H-K", "W1-W2", "W2-W3"])
        })
        
        # Rate limiting
        time.sleep(1.0)
    
    # Save
    output = {
        "metadata": {
            "source": "v9.0 TOP 10 verification",
            "compiled_date": time.strftime("%Y-%m-%d"),
            "note": "Known pulsars (negative training samples)"
        },
        "pulsars": pulsars
    }
    
    output_path = Path(__file__).parent.parent / "data" / "known_pulsars_features.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Saved {len(pulsars)} pulsars to: {output_path}")
    print(f"[STATS] With features: {sum(1 for p in pulsars if p.get('has_features', False))}/{len(pulsars)}")
    return output_path

if __name__ == "__main__":
    get_known_pulsar_features()
