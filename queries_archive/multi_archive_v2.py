"""BlackHole Beacon — Multi-Archive Expansion v2.0

Adds IRAS PSC and ROSAT RASS via VizieR.
Extends the existing irsa_query_engine.py.
"""

import json, os, sys, time, csv
from datetime import datetime
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR_DIR = os.path.join(ROOT, "catalog")
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

RADIUS = 15 * u.arcsec
OUT_FILE = os.path.join(DATA_DIR, "multi_archive_results.json")

print("BlackHole Beacon — Multi-Archive Expansion v2.0")
print("="*50)

# ==============================
# 1. Load anchors
# ==============================
print("\n--- Load Anchors ---")
anchors = []
for fname, atype in [("psrcat_catalog.csv", "pulsar"),
                      ("bh_xrb_catalog.csv", "bh_xrb"),
                      ("smbh_catalog.csv", "smbh")]:
    fpath = os.path.join(ANCHOR_DIR, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                ra = float(row.get("RA_deg", 0))
                dec = float(row.get("Dec_deg", 0))
                if ra == 0 and dec == 0:
                    continue
                anchars.append({
                    "name": (row.get("JName") or row.get("Name") or "").strip(),
                    "ra": ra, "dec": dec, "type": atype,
                })
            except (ValueError, KeyError):
                continue

print(f"Loaded {len(anchors)} anchors")
if not anchars:
    print("No anchors loaded. Exiting.")
    sys.exit(1)

# ==============================
# 2. IRAS PSC via VizieR (VIII/199)
# ==============================
print("\n--- IRAS PSC (VIII/199) ---")
Vizier.ROW_LIMIT = 10

iras_matches = []
fail = 0
t0 = time.time()

for i, a in enumerate(anchors[:50]):  # Test first 50
    if i % 10 == 0:
        print(f"  {i}/{min(50, len(anchors))}...", end="", flush=True)
    try:
        cat = Vizier.query_region(
            SkyCoord(a["ra"], a["dec"], unit="deg"),
            radius=RADIUS,
            catalog=["VIII/199/iras"]
        )
        if cat and len(cat[0]) > 0:
            for row in cat[0]:
                iras_matches.append({
                    "anchor": a["name"],
                    "f12": float(row["F12"]) if row["F12"] else None,
                    "f25": float(row["F25"]) if row["F25"] else None,
                    "f60": float(row["F60"]) if row["F60"] else None,
                    "f100": float(row["F100"]) if row["F100"] else None,
                })
    except Exception as e:
        fail += 1
        pass

print(f"\n  IRAS matches: {len(iras_matches)} / 50 anchors (fail: {fail})")
print(f"  Time: {time.time()-t0:.1f}s")

# ==============================
# 3. ROSAT RASS via VizieR (IX/29/rass)
# ==============================
print("\n--- ROSAT RASS (IX/29/rass) ---")
Vizier.ROW_LIMIT = 10

rosat_matches = []
fail = 0
t0 = time.time()

for i, a in enumerate(anchors[:50]):  # Test first 50
    if i % 10 == 0:
        print(f"  {i}/{min(50, len(anchors))}...", end="", flush=True)
    try:
        cat = Vizier.query_region(
            SkyCoord(a["ra"], a["dec"], unit="deg"),
            radius=RADIUS,
            catalog=["IX/29/rass"]
        )
        if cat and len(cat[0]) > 0:
            for row in cat[0]:
                rosat_matches.append({
                    "anchor": a["name"],
                    "ra": float(row["RAJ2000"]) if row["RAJ2000"] else None,
                    "dec": float(row["DEJ2000"]) if row["DEJ2000"] else None,
                    "cts": float(row["CTS"]) if row["CTS"] else None,
                    "hr1": float(row["HR1"]) if row["HR1"] else None,
                })
    except Exception as e:
        fail += 1
        pass

print(f"\n  ROSAT matches: {len(rosat_matches)} / 50 anchors (fail: {fail})")
print(f"  Time: {time.time()-t0:.1f}s")

# ==============================
# 4. Save results
# ==============================
print("\n--- Save Results ---")
result = {
    "iras_psc": iras_matches,
    "rosat_rass": rosat_matches,
    "generated": datetime.now().isoformat(),
    "test_anchors": 50,
}

with open(OUT_FILE, "w") as f:
    json.dump(result, f, indent=2, default=str)

print(f"Saved: {OUT_FILE}")
print("\nDone.")
