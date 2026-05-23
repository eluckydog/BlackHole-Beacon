"""
BlackHole Beacon — Real Negative Sample Collector v2.0

Collects REAL astrophysical objects that CONFUSE with pulsar/BH signals:
1. AGN/Quasars (red in WISE, but no proper motion)
2. White Dwarfs (high PM, but blue in IR)
3. Brown Dwarfs (high PM, red in IR, but not compact)
4. YSO (red in IR, variable, but not compact)
5. AGB stars (red in IR, variable, but not compact)
6. CV (variable, but blue in IR)
7. Flare stars (variable, but blue in IR)

These are REAL negative samples (with labels), not synthetic ones.

Uses Simbad TAP (ADQL) which is the modern/preferred method.
"""

import json
import os
import sys
import time
from datetime import datetime

# ==========
# 1. Check dependencies
# ==========
try:
    from astroquery.simbad import Simbad
    HAS_SIMBAD = True
except ImportError:
    HAS_SIMBAD = False
    print("ERROR: astroquery.simbad not available")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUT_FILE = os.path.join(DATA_DIR, "real_negative_samples_v2.json")

print("BlackHole Beacon — Real Negative Sample Collector v2.0 (ADQL)")
print("="*70)

# ==========
# 2. Negative sample definitions (SIMBAD otype codes)
# ==========
NEGATIVE_TYPES = [
    {
        "name": "AGN",
        "otype": "QSO",  # Quasar (includes AGN)
        "description": "Quasars & Active Galactic Nuclei (red in WISE, no PM)",
        "limit": 200
    },
    {
        "name": "WD",
        "otype": "WD",  # White Dwarf
        "description": "White Dwarfs (high PM, blue in IR)",
        "limit": 200
    },
    {
        "name": "BD",
        "otype": "BD",  # Brown Dwarf
        "description": "Brown Dwarfs (high PM, red in IR, but not compact)",
        "limit": 150
    },
    {
        "name": "YSO",
        "otype": "Y*O",  # Young Stellar Object
        "description": "Young Stellar Objects (red in IR, variable)",
        "limit": 150
    },
    {
        "name": "AGB",
        "otype": "ABG",  # Asymptotic Giant Branch
        "description": "AGB stars & Mira variables (red in IR, variable)",
        "limit": 150
    },
    {
        "name": "CV",
        "otype": "CV*",  # Cataclysmic Variable
        "description": "Cataclysmic Variables (variable, blue in IR)",
        "limit": 100
    },
    {
        "name": "Flare",
        "otype": "Er*",  # Eruptive variable (includes flare stars)
        "description": "Flare stars (variable, blue in IR)",
        "limit": 100
    }
]

# ==========
# 3. Collect from SIMBAD TAP (ADQL)
# ==========
def collect_simbad_tap():
    """Use Simbad TAP query (ADQL) to collect negative samples."""
    if not HAS_SIMBAD:
        print("\n  [SKIP] Simbad TAP: astroquery.simbad not available")
        return []
    
    print("\n--- Method: Simbad TAP (ADQL) ---")
    print("  Using ADQL queries (modern Simbad API)\n")
    
    all_samples = []
    
    for nt in NEGATIVE_TYPES:
        name = nt["name"]
        otype = nt["otype"]
        limit = nt["limit"]
        desc = nt["description"]
        
        print(f"  Querying {name} ({desc})...")
        print(f"    ADQL: SELECT TOP {limit} * FROM basic WHERE otype='{otype}'")
        
        try:
            # Construct ADQL query
            adql = f"""
            SELECT TOP {limit}
                main_id, ra, dec, pmra, pmdec, plx,
                flux_j, flux_h, flux_k, flux_w1, flux_w2, flux_w3, flux_w4
            FROM basic
            WHERE otype='{otype}'
            """
            
            # Execute TAP query
            result = Simbad.query_tap(adql.strip())
            
            if result is None or len(result) == 0:
                print(f"    [EMPTY] No {name} found")
                continue
            
            print(f"    [OK] Got {len(result)} {name}")
            
            # Convert to our format
            for row in result:
                # Handle byte strings (Simbad returns bytes for string columns)
                main_id = row["main_id"]
                if isinstance(main_id, bytes):
                    main_id = main_id.decode("utf-8")
                
                # Helper: safely convert to float
                def to_float(val):
                    if val is None:
                        return None
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
                
                sample = {
                    "name": main_id,
                    "type": name,
                    "ra": to_float(row["ra"]),
                    "dec": to_float(row["dec"]),
                    "pm_ra": to_float(row["pmra"]),
                    "pm_dec": to_float(row["pmdec"]),
                    "plx": to_float(row["plx"]),
                    "J": to_float(row["flux_j"]),
                    "H": to_float(row["flux_h"]),
                    "K": to_float(row["flux_k"]),
                    "W1": to_float(row["flux_w1"]),
                    "W2": to_float(row["flux_w2"]),
                    "W3": to_float(row["flux_w3"]),
                    "W4": to_float(row["flux_w4"]),
                    "source": "SIMBAD_TAP_ADQL",
                    "is_negative": True,
                    "otype": otype
                }
                
                all_samples.append(sample)
            
            # Rate limit (be nice to Simbad server)
            time.sleep(1)
            
        except Exception as e:
            print(f"    [ERROR] {e}")
            continue
    
    print(f"\n  Total collected from Simbad TAP: {len(all_samples)}")
    return all_samples

# ==========
# 4. Save results
# ==========
def save_results(samples):
    """Save collected negative samples to JSON."""
    print(f"\n--- Saving {len(samples)} negative samples ---")
    
    # Add metadata
    output = {
        "metadata": {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "source": "Real astrophysical confusing sources (SIMBAD TAP)",
            "description": "These are REAL objects that CONFUSE with pulsar/BH signals",
            "total": len(samples),
            "types": list(set([s["type"] for s in samples])),
            "note": "Collected via ADQL queries to SIMBAD TAP service"
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
# 5. Main
# ==========
def main():
    all_samples = []
    
    # Try Simbad TAP (ADQL)
    samples_tap = collect_simbad_tap()
    all_samples.extend(samples_tap)
    
    # If still empty, warn
    if len(all_samples) == 0:
        print("\n  [WARNING] No real negative samples collected!")
        print("  [INFO] Please check Simbad TAP connectivity.")
        print("  [INFO] Falling back to synthetic negatives...")
        
        # Create minimal synthetic negatives (last resort)
        print("  [INFO] Creating minimal synthetic negatives...")
        synthetic = create_synthetic_negatives(100)
        all_samples.extend(synthetic)
    
    # Save
    save_results(all_samples)
    
    print("\n" + "="*70)
    print(f"DONE. Total negative samples: {len(all_samples)}")
    print("="*70)

def create_synthetic_negatives(n=100):
    """Create minimal synthetic negatives (last resort)."""
    import random
    samples = []
    for i in range(n):
        samples.append({
            "name": f"SYNTHETIC_{i}",
            "type": "SYNTHETIC",
            "ra": random.uniform(0, 360),
            "dec": random.uniform(-90, 90),
            "pm_ra": random.uniform(-5, 5),
            "pm_dec": random.uniform(-5, 5),
            "plx": random.uniform(0, 1),
            "J": random.uniform(14, 18),
            "H": random.uniform(13.5, 17.5),
            "K": random.uniform(13, 17),
            "W1": random.uniform(12, 16),
            "W2": random.uniform(11.5, 15.5),
            "W3": random.uniform(8, 12),
            "W4": random.uniform(6, 10),
            "source": "SYNTHETIC_FALLBACK",
            "is_negative": True
        })
    return samples

if __name__ == "__main__":
    main()
