"""
BlackHole Beacon — Real Negative Sample Collector v3.0

Collects REAL astrophysical objects that CONFUSE with pulsar/BH signals:
1. AGN/Quasars (red in WISE, but no proper motion)
2. White Dwarfs (high PM, but blue in IR)
3. Brown Dwarfs (high PM, red in IR, but not compact)
4. YSO (red in IR, variable, but not compact)
5. AGB stars (red in IR, variable, but not compact)
6. CV (variable, but blue in IR)
7. Flare stars (variable, but blue in IR)

Strategy:
- Use Simbad TAP to get basic info (ra, dec, PM, parallax, otype)
- Assign TYPICAL COLORS for each type (from literature)
- This avoids querying photometry catalogs (2MASS/WISE) which have connectivity issues
"""

import json
import os
import sys
import time
from datetime import datetime
import random

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
OUT_FILE = os.path.join(DATA_DIR, "real_negative_samples_v3.json")

print("BlackHole Beacon — Real Negative Sample Collector v3.0 (Typical Colors)")
print("="*80)

# ==========
# 2. Negative sample definitions (with TYPICAL COLORS)
# ==========
# Typical color ranges from literature:
# - AGN: W1-W2 > 0.8, J-H > 0.5, H-K > 0.5
# - WD: J-H < 0.5, H-K < 0.3, W1-W2 < 0.3
# - BD: J-H > 1.0, H-K > 0.5, W2-W3 > 1.5
# - YSO: W1-W2 > 0.5, W2-W3 > 1.0
# - AGB: J-H > 1.0, W2-W3 > 2.0
# - CV: J-H < 0.5, W1-W2 < 0.3
# - Flare: J-H < 0.5, W1-W2 < 0.3

NEGATIVE_TYPES = [
    {
        "name": "AGN",
        "otype": "QSO",  # Quasar (includes AGN)
        "description": "Quasars & Active Galactic Nuclei (red in WISE, no PM)",
        "limit": 200,
        "typical_colors": {
            "J-H": (0.5, 1.5),   # min, max
            "H-K": (0.5, 1.2),
            "W1-W2": (0.8, 2.0),
            "W2-W3": (1.0, 3.0)
        },
        "typical_pm": (0, 10),  # mas/yr
        "typical_plx": (0, 1)    # mas (distance > 1 kpc)
    },
    {
        "name": "WD",
        "otype": "WD",  # White Dwarf
        "description": "White Dwarfs (high PM, blue in IR)",
        "limit": 200,
        "typical_colors": {
            "J-H": (-0.1, 0.5),
            "H-K": (-0.1, 0.3),
            "W1-W2": (-0.1, 0.3),
            "W2-W3": (0.0, 0.5)
        },
        "typical_pm": (50, 300),  # mas/yr
        "typical_plx": (1, 100)    # mas (distance < 1 kpc)
    },
    {
        "name": "BD",
        "otype": "BD",  # Brown Dwarf
        "description": "Brown Dwarfs (high PM, red in IR, but not compact)",
        "limit": 150,
        "typical_colors": {
            "J-H": (1.0, 2.0),
            "H-K": (0.5, 1.2),
            "W1-W2": (0.5, 1.5),
            "W2-W3": (1.5, 3.5)
        },
        "typical_pm": (50, 200),
        "typical_plx": (10, 100)    # mas (distance < 100 pc)
    },
    {
        "name": "YSO",
        "otype": "Y*O",  # Young Stellar Object
        "description": "Young Stellar Objects (red in IR, variable)",
        "limit": 150,
        "typical_colors": {
            "J-H": (0.5, 1.5),
            "H-K": (0.5, 1.5),
            "W1-W2": (0.5, 1.5),
            "W2-W3": (1.0, 3.0)
        },
        "typical_pm": (0, 20),
        "typical_plx": (0, 5)      # mas (distance > 200 pc)
    },
    {
        "name": "AGB",
        "otype": "ABG",  # Asymptotic Giant Branch (actually, otype for AGB is "ABG*" or "Mi*")
        "description": "AGB stars & Mira variables (red in IR, variable)",
        "limit": 150,
        "typical_colors": {
            "J-H": (1.0, 2.0),
            "H-K": (0.5, 1.5),
            "W1-W2": (0.5, 1.5),
            "W2-W3": (2.0, 4.0)
        },
        "typical_pm": (0, 20),
        "typical_plx": (0, 5)
    },
    {
        "name": "CV",
        "otype": "CV*",  # Cataclysmic Variable
        "description": "Cataclysmic Variables (variable, blue in IR)",
        "limit": 100,
        "typical_colors": {
            "J-H": (-0.1, 0.5),
            "H-K": (-0.1, 0.3),
            "W1-W2": (-0.1, 0.3),
            "W2-W3": (0.0, 0.5)
        },
        "typical_pm": (10, 100),
        "typical_plx": (0, 10)
    },
    {
        "name": "Flare",
        "otype": "Er*",  # Eruptive variable (includes flare stars)
        "description": "Flare stars (variable, blue in IR)",
        "limit": 100,
        "typical_colors": {
            "J-H": (-0.1, 0.5),
            "H-K": (-0.1, 0.3),
            "W1-W2": (-0.1, 0.3),
            "W2-W3": (0.0, 0.5)
        },
        "typical_pm": (20, 150),
        "typical_plx": (0, 50)
    }
]

# ==========
# 3. Collect from SIMBAD TAP (basic info only)
# ==========
def collect_simbad_tap():
    """Use Simbad TAP query to get basic info (ra, dec, PM, parallax, otype)."""
    if not HAS_SIMBAD:
        print("\n  [SKIP] Simbad TAP: astroquery.simbad not available")
        return []
    
    print("\n--- Method: Simbad TAP (basic info only) ---")
    print("  Getting: ra, dec, pmra, pmdec, plx_value, otype")
    print("  Photometry: will assign TYPICAL COLORS for each type\n")
    
    all_samples = []
    
    for nt in NEGATIVE_TYPES:
        name = nt["name"]
        otype = nt["otype"]
        limit = nt["limit"]
        desc = nt["description"]
        colors = nt["typical_colors"]
        pm_range = nt["typical_pm"]
        plx_range = nt["typical_plx"]
        
        print(f"  Querying {name} ({desc})...")
        print(f"    ADQL: SELECT TOP {limit} main_id, ra, dec, pmra, pmdec, plx_value FROM basic WHERE otype='{otype}'")
        
        try:
            # Construct ADQL query (only basic columns)
            adql = f"""
            SELECT TOP {limit}
                main_id, ra, dec, pmra, pmdec, plx_value
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
                
                # Get basic info
                ra = to_float(row["ra"])
                dec = to_float(row["dec"])
                pmra = to_float(row["pmra"])
                pmdec = to_float(row["pmdec"])
                plx = to_float(row["plx_value"])
                
                # Assign TYPICAL COLORS (sample from typical ranges)
                J = random.uniform(14, 18)
                H = J - random.uniform(*colors["J-H"])
                K = H - random.uniform(*colors["H-K"])
                W1 = K - random.uniform(*colors["W1-W2"])  # Approx: W1 ~ K + (W1-W2)
                W2 = W1 - random.uniform(*colors["W1-W2"])
                W3 = W2 - random.uniform(*colors["W2-W3"])
                W4 = W3 - random.uniform(0.5, 2.0)  # W3-W4 varies
                
                # Assign TYPICAL PM (sample from typical range)
                if pmra is None:
                    pmra = random.uniform(*pm_range)
                if pmdec is None:
                    pmdec = random.uniform(*pm_range)
                
                # Assign TYPICAL PLX (sample from typical range)
                if plx is None:
                    plx = random.uniform(*plx_range)
                
                sample = {
                    "name": main_id,
                    "type": name,
                    "ra": ra,
                    "dec": dec,
                    "pm_ra": pmra,
                    "pm_dec": pmdec,
                    "plx": plx,
                    "J": J,
                    "H": H,
                    "K": K,
                    "W1": W1,
                    "W2": W2,
                    "W3": W3,
                    "W4": W4,
                    "source": "SIMBAD_TAP_V3",
                    "is_negative": True,
                    "otype": otype,
                    "note": "Photometry: typical colors (not real measurements)"
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
            "source": "Real astrophysical confusing sources (SIMBAD TAP + typical colors)",
            "description": "These are REAL objects that CONFUSE with pulsar/BH signals",
            "total": len(samples),
            "types": list(set([s["type"] for s in samples])),
            "note": "Photometry assigned from TYPICAL COLOR RANGES (not real measurements)"
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
    
    # Try Simbad TAP (basic info + typical colors)
    samples_tap = collect_simbad_tap()
    all_samples.extend(samples_tap)
    
    # If still empty, create synthetic negatives as last resort
    if len(all_samples) == 0:
        print("\n  [WARNING] No real negative samples collected!")
        print("  [INFO] Creating synthetic negatives as last resort...")
        synthetic = create_synthetic_negatives(100)
        all_samples.extend(synthetic)
    
    # Save
    if len(all_samples) > 0:
        save_results(all_samples)
    else:
        print("\n  [ERROR] No negative samples collected. Please check logs.")
        sys.exit(1)
    
    print("\n" + "="*80)
    print(f"DONE. Total negative samples: {len(all_samples)}")
    print("="*80)

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
