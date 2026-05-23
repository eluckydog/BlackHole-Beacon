"""Quick VizieR test: IRAS PSC + ROSAT RASS"""
import os, csv
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_DIR = os.path.join(ROOT, "catalog")

# Load first anchor
fpath = os.path.join(CATALOG_DIR, "psrcat_catalog.csv")
with open(fpath, encoding="utf-8") as f:
    r = next(csv.DictReader(f))
    ra = float(r["RA_deg"])
    dec = float(r["Dec_deg"])
    name = (r.get("JName") or r.get("Name") or "").strip()
    print(f"Test anchor: {name}  ra={ra:.3f} dec={dec:.3f}")

Vizier.ROW_LIMIT = 5

# Test IRAS PSC (VIII/199)
print("\n--- IRAS PSC (VIII/199) ---")
try:
    cat = Vizier.query_region(
        SkyCoord(ra, dec, unit="deg"),
        radius=15 * u.arcsec,
        catalog=["VIII/199/iras"]
    )
    if cat and len(cat[0]) > 0:
        print(f"  OK: {len(cat[0])} rows")
        print(f"  Columns: {list(cat[0].colnames)[:8]}")
    else:
        print("  No match")
except Exception as e:
    print(f"  Error: {e}")

# Test ROSAT RASS (IX/29/rass)
print("\n--- ROSAT RASS (IX/29/rass) ---")
try:
    cat2 = Vizier.query_region(
        SkyCoord(ra, dec, unit="deg"),
        radius=15 * u.arcsec,
        catalog=["IX/29/rass"]
    )
    if cat2 and len(cat2[0]) > 0:
        print(f"  OK: {len(cat2[0])} rows")
        print(f"  Columns: {list(cat2[0].colnames)[:8]}")
    else:
        print("  No match")
except Exception as e:
    print(f"  Error: {e}")
