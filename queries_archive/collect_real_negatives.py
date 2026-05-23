"""
BlackHole Beacon — Real Negative Sample Collector v1.0

Collects REAL astrophysical objects that CONFUSE with pulsar/BH signals:
1. AGN/Quasars (red in WISE, but no proper motion)
2. White Dwarfs (high PM, but blue in IR)
3. Brown Dwarfs (high PM, red in IR, but not compact)
4. YSO (red in IR, variable, but not compact)
5. AGB stars (red in IR, variable, but not compact)
6. CV (variable, but blue in IR)
7. Flare stars (variable, but blue in IR)

These are REAL negative samples (with labels), not synthetic ones.
"""

import json
import os
import sys
import time
import random
from datetime import datetime

# ==========
# 1. Try astroquery.Simbad TAP (preferred)
# ==========
try:
    from astroquery.simbad import Simbad
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    HAS_SIMBAD = True
except ImportError:
    HAS_SIMBAD = False
    print("WARNING: astroquery.simbad not available")

# ==========
# 2. Try astroquery.VizieR (fallback)
# ==========
try:
    from astroquery.vizier import Vizier
    HAS_VIZIER = True
except ImportError:
    HAS_VIZIER = False
    print("WARNING: astroquery.vizier not available")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUT_FILE = os.path.join(DATA_DIR, "real_negative_samples.json")

print("BlackHole Beacon — Real Negative Sample Collector v1.0")
print("="*60)

# ==========
# Negative sample definitions
# ==========
NEGATIVE_TYPES = [
    {
        "name": "AGN",
        "simbad_criteria": "otype='QSO' OR otype='AGN'",
        "description": "Quasars & Active Galactic Nuclei (red in WISE, no PM)",
        "expected_color": "W1-W2 > 0.8",
        "expected_pm": "< 10 mas/yr",
        "limit": 200
    },
    {
        "name": "WD",
        "simbad_criteria": "otype='WD'",
        "description": "White Dwarfs (high PM, blue in IR)",
        "expected_color": "J-H < 0.5, W1-W2 < 0.3",
        "expected_pm": "> 50 mas/yr",
        "limit": 200
    },
    {
        "name": "BD",
        "simbad_criteria": "otype='BD' OR otype='L0' OR otype='T0'",
        "description": "Brown Dwarfs (high PM, red in IR, but not compact)",
        "expected_color": "J-H > 1.0, W2-W3 > 1.5",
        "expected_pm": "> 50 mas/yr",
        "limit": 150
    },
    {
        "name": "YSO",
        "simbad_criteria": "otype='Y*O'",
        "description": "Young Stellar Objects (red in IR, variable)",
        "expected_color": "W1-W2 > 0.5, W2-W3 > 1.0",
        "expected_pm": "< 20 mas/yr",
        "limit": 150
    },
    {
        "name": "AGB",
        "simbad_criteria": "otype='ABG' OR otype='Mi*'",
        "description": "AGB stars & Mira variables (red in IR, variable)",
        "expected_color": "J-H > 1.0, W2-W3 > 2.0",
        "expected_pm": "< 20 mas/yr",
        "limit": 150
    },
    {
        "name": "CV",
        "simbad_criteria": "otype='CV*'",
        "description": "Cataclysmic Variables (variable, blue in IR)",
        "expected_color": "J-H < 0.5, W1-W2 < 0.3",
        "expected_pm": "10-100 mas/yr",
        "limit": 100
    },
    {
        "name": "Flare",
        "simbad_criteria": "otype='Er*' OR otype='Flare*'",
        "description": "Flare stars (variable, blue in IR)",
        "expected_color": "J-H < 0.5, W1-W2 < 0.3",
        "expected_pm": "20-150 mas/yr",
        "limit": 100
    }
]

# ==========
# 3. Collect from SIMBAD TAP
# ==========
def collect_simbad_tap(negative_types):
    """Use Simbad TAP query to collect negative samples."""
    if not HAS_SIMBAD:
        print("  [SKIP] Simbad TAP: astroquery.simbad not available")
        return []
    
    print("\n--- Method 1: Simbad TAP query ---")
    
    all_samples = []
    
    try:
        # Enable all fields
        Simbad.reset_votable_fields()
        Simbad.add_votable_fields("pm", "plx", "flux(J,H,K,W1,W2,W3,W4)")
        
        for nt in negative_types:
            name = nt["name"]
            criteria = nt["simbad_criteria"]
            limit = nt["limit"]
            
            print(f"\n  Querying {name} ({nt['description']})...")
            
            try:
                # Use query_criteria (if still works) or query_tap
                # query_criteria is deprecated, use query_tap instead
                # But query_tap requires ADQL knowledge, let's try query_criteria first
                result = Simbad.query_criteria(criteria, limit=limit)
                
                if result is None or len(result) == 0:
                    print(f"    [EMPTY] No {name} found")
                    continue
                
                print(f"    [OK] Got {len(result)} {name}")
                
                # Convert to our format
                for row in result:
                    sample = {
                        "name": row["MAIN_ID"] if "MAIN_ID" in row.colnames else f"{name}_{len(all_samples)}",
                        "type": name,
                        "ra": float(row["RA"]) if "RA" in row.colnames and row["RA"] else None,
                        "dec": float(row["DEC"]) if "DEC" in row.colnames and row["DEC"] else None,
                        "pm_ra": float(row["PMRA"]) if "PMRA" in row.colnames and row["PMRA"] else None,
                        "pm_dec": float(row["PMDEC"]) if "PMDEC" in row.colnames and row["PMDEC"] else None,
                        "plx": float(row["PLX"]) if "PLX" in row.colnames and row["PLX"] else None,
                        "J": float(row["FLUX_J"]) if "FLUX_J" in row.colnames and row["FLUX_J"] else None,
                        "H": float(row["FLUX_H"]) if "FLUX_H" in row.colnames and row["FLUX_H"] else None,
                        "K": float(row["FLUX_K"]) if "FLUX_K" in row.colnames and row["FLUX_K"] else None,
                        "W1": float(row["FLUX_W1"]) if "FLUX_W1" in row.colnames and row["FLUX_W1"] else None,
                        "W2": float(row["FLUX_W2"]) if "FLUX_W2" in row.colnames and row["FLUX_W2"] else None,
                        "W3": float(row["FLUX_W3"]) if "FLUX_W3" in row.colnames and row["FLUX_W3"] else None,
                        "W4": float(row["FLUX_W4"]) if "FLUX_W4" in row.colnames and row["FLUX_W4"] else None,
                        "source": "SIMBAD_TAP",
                        "is_negative": True
                    }
                    all_samples.append(sample)
                
                # Rate limit
                time.sleep(1)
                
            except Exception as e:
                print(f"    [ERROR] {e}")
                continue
        
        print(f"\n  Total collected from Simbad TAP: {len(all_samples)}")
        return all_samples
        
    except Exception as e:
        print(f"  [ERROR] Simbad TAP failed: {e}")
        return []

# ==========
# 4. Collect from VizieR (fallback)
# ==========
def collect_vizier(negative_types):
    """Use VizieR to collect negative samples."""
    if not HAS_VIZIER:
        print("\n  [SKIP] VizieR: astroquery.vizier not available")
        return []
    
    print("\n--- Method 2: VizieR query (fallback) ---")
    print("  [INFO] VizieR is not implemented yet (need catalog IDs)")
    print("  [INFO] Will use Simbad TAP result only")
    return []

# ==========
# 5. Save results
# ==========
def save_results(samples):
    """Save collected negative samples to JSON."""
    print(f"\n--- Saving {len(samples)} negative samples ---")
    
    # Add metadata
    output = {
        "metadata": {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "source": "Real astrophysical confusing sources",
            "description": "These are REAL objects that CONFUSE with pulsar/BH signals",
            "total": len(samples),
            "types": list(set([s["type"] for s in samples]))
        },
        "samples": samples
    }
    
    with open(OUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"  Saved: {OUT_FILE}")
    
    # Print statistics
    print(f"\n  Breakdown by type:")
    type_counts = {}
    for s in samples:
        t = s["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")

# ==========
# 6. Main
# ==========
def main():
    all_samples = []
    
    # Try Simbad TAP first
    samples_tap = collect_simbad_tap(NEGATIVE_TYPES)
    all_samples.extend(samples_tap)
    
    # Try VizieR (fallback)
    if len(all_samples) < 100:
        samples_vizier = collect_vizier(NEGATIVE_TYPES)
        all_samples.extend(samples_vizier)
    
    # If still empty, create synthetic negatives as last resort
    if len(all_samples) == 0:
        print("\n  [WARNING] No real negative samples collected!")
        print("  [INFO] Creating synthetic negatives as last resort...")
        # (Will not create here, just warn)
    
    # Save
    if len(all_samples) > 0:
        save_results(all_samples)
    else:
        print("\n  [ERROR] No negative samples collected. Please check logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
