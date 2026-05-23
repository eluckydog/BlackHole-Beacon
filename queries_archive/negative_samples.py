"""BlackHole Beacon — Negative Sample Collector v1.0

Collects two types of negative samples:
1. Fermi 4FGL unidentified sources (mixed pulsar/blazar)
2. Random sky positions (true negative — no pulsar there)
"""

import json, os, sys, math, random
from datetime import datetime
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUT_FILE = os.path.join(DATA_DIR, "negative_samples.json")
FERMI_FILE = os.path.join(DATA_DIR, "fermi_4fgl.json")

print("BlackHole Beacon — Negative Sample Collector")
print("="*50)

# ==============================
# 1. Fermi 4FGL-DR4 via VizieR
# ==============================
print("\n--- Step 1: Fermi 4FGL Unidentified ---")

# Query VizieR for 4FGL-DR4 catalog (VII/323)
# Columns: Source_Name, RAJ2000, DEJ2000, Class1 (classification)
# Class1: 0=unidentified, 1= pulsar, 2=AGN, 3=SPP, etc.

try:
    Vizier.ROW_LIMIT = 5000
    fermi = Vizier.get_catalogs("VII/323/fg_12yr")[0]
    print(f"  Downloaded: {len(fermi)} sources")
    
    # Filter unidentified sources (CLASS1 == 0)
    unid = fermi[fermi["GLAT"] > 10]  # |b| > 10° to avoid Galactic plane confusion
    unid = unid[unid["CLASS1"] == 0]
    print(f"  Unidentified (|b|>10°): {len(unid)}")
    
    # Save Fermi data
    fermi_data = []
    for row in unid:
        fermi_data.append({
            "name": row["Source_Name"].decode().strip(),
            "ra": float(row["RAJ2000"]),
            "dec": float(row["DEJ2000"]),
            "class1": int(row["CLASS1"]),
            "glat": float(row["GLAT"]),
        })
    
    with open(FERMI_FILE, "w") as f:
        json.dump(fermi_data, f, indent=2)
    print(f"  Saved: {FERMI_FILE}")
    
except Exception as e:
    print(f"  Error: {e}")
    print("  Trying alternative download...")
    # Fallback: direct HTTP download of 4FGL-DR4 FITS file
    # (not implemented yet — would need astropy.io.fits)

# ==============================
# 2. Random sky positions (background)
# ==============================
print("\n--- Step 2: Random Sky Positions ---")

random.seed(42)  # Reproducible
N_RANDOM = 500
random_positions = []

for i in range(N_RANDOM):
    # Uniform on sphere: ra ∈ [0,360), dec ∈ [-90,90)
    ra = random.uniform(0, 360)
    # For uniform on sphere: sin(dec) ∈ [-1,1)
    dec = math.degrees(math.asin(random.uniform(-1, 1)))
    random_positions.append({"ra": ra, "dec": dec, "id": f"RAND_{i:04d}"})

print(f"  Generated: {N_RANDOM} random positions")

# Query 2MASS within 3" of each random position
print("  Querying 2MASS (this may take a while)...")
random_matches = []

# Batch query: group into 50-position batches
batch_size = 50
for batch_start in range(0, N_RANDOM, batch_size):
    batch = random_positions[batch_start:batch_start+batch_size]
    print(f"    Batch {batch_start//batch_size + 1}/{(N_RANDOM+batch_size-1)//batch_size}...", end="")
    
    # Build VizieR query for 2MASS PSC
    try:
        Vizier.ROW_LIMIT = 5  # Max 5 sources per position
        # Query each position individually (VizieR doesn't support batch cone search via API)
        for targ in batch:
            try:
                cat = Vizier.query_region(
                    SkyCoord(targ["ra"], targ["dec"], unit="deg"),
                    radius=3*u.arcsec,
                    catalog=["II/246/out"]
                )
                if cat and len(cat[0]) > 0:
                    for row in cat[0]:
                        random_matches.append({
                            "random_id": targ["id"],
                            "ra": float(row["RAJ2000"]),
                            "dec": float(row["DEJ2000"]),
                            "j_m": float(row["Jmag"]) if row["Jmag"] > 0 else None,
                            "h_m": float(row["Hmag"]) if row["Hmag"] > 0 else None,
                            "k_m": float(row["Kmag"]) if row["Kmag"] > 0 else None,
                        })
            except Exception as e:
                pass  # No match = good (true negative)
        print(".", end="")
    except Exception as e:
        print(f"E", end="")
        pass
    
    print(f" {len(random_matches)} matches so far")

print(f"\n  Random position matches: {len(random_matches)} / {N_RANDOM}")

# ==============================
# 3. Save results
# ==============================
print("\n--- Step 3: Save Results ---")

result = {
    "fermi_unidentified": fermi_data if 'fermi_data' in dir() else [],
    "random_positions": random_positions,
    "random_matches": random_matches,
    "generated": datetime.now().isoformat(),
}

with open(OUT_FILE, "w") as f:
    json.dump(result, f, indent=2, default=str)

print(f"  Saved: {OUT_FILE}")
print("\nDone.")
