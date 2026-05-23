"""
Query ALL known black hole X-ray binaries from Simbad
Use otype='BH*' or 'HXB' or 'LXB' to get confirmed BH XRBs
"""
import sys
import json
import time
from pathlib import Path

try:
    from astroquery.simbad import Simbad
    from astropy.table import Table
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    import numpy as np
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Install: pip install astroquery astropy")
    sys.exit(1)

# -- Output file --
OUT_FILE = Path(__file__).parent.parent / "data" / "all_known_bh_xrb_simbad.json"

# -- Otypes for black hole X-ray binaries --
# BH* = Black hole candidate (general)
# HXB = High-mass X-ray Binary
# LXB = Low-mass X-ray Binary
# XB* = X-ray binary (general)
OTYPES = ["BH*", "HXB", "LXB", "XB*"]

def query_bh_xrb_by_otype(otype: str, max_rows: int = 500):
    """Query Simbad for objects of given otype, filter for BH-related."""
    print(f"[INFO] Querying Simbad for otype='{otype}' (max {max_rows} rows)...")
    try:
        Simbad.reset_votable_fields()
        Simbad.add_votable_fields(["otype", "coordinates", "ids", "pm", "plx"])
        # This may take a while
        result = Simbad.query_criteria(otype=otype, maxrows=max_rows)
        if result is None or len(result) == 0:
            print(f"[WARN] No results for otype={otype}")
            return []
        print(f"[OK] Got {len(result)} rows for otype={otype}")
        # Convert to list of dicts
        records = []
        for row in result:
            main_id = row["main_id"]
            ra = row["ra"]
            dec = row["dec"]
            otype_val = row["otype"]
            # Fetch IDs to check if it's a known BH
            ids = row["ids"] if "ids" in row else []
            # Check if IDs contain "BH" or "black hole"
            is_bh = False
            for id_str in ids:
                if "BH" in id_str.upper() or "BLACK HOLE" in id_str.upper():
                    is_bh = True
                    break
            records.append({
                "main_id": main_id,
                "ra": ra,
                "dec": dec,
                "otype": otype_val,
                "is_bh_candidate": is_bh,
                "ids": ids[:10]  # truncate
            })
        return records
    except Exception as e:
        print(f"[ERROR] Query failed for otype={otype}: {e}")
        return []

def main():
    all_records = []
    for ot in OTYPES:
        recs = query_bh_xrb_by_otype(ot, max_rows=500)
        all_records.extend(recs)
        time.sleep(1)  # be nice to Simbad
    
    # Deduplicate by main_id
    seen = set()
    unique = []
    for r in all_records:
        mid = r["main_id"]
        if mid not in seen:
            seen.add(mid)
            unique.append(r)
    
    print(f"[INFO] Total unique records: {len(unique)}")
    
    # Save
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "Simbad query_criteria",
                "otypes": OTYPES,
                "query_date": time.strftime("%Y-%m-%d"),
                "total_unique": len(unique)
            },
            "records": unique
        }, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved {len(unique)} records to: {OUT_FILE}")
    
    # Print first 20
    print("\n--- First 20 records ---")
    for i, r in enumerate(unique[:20]):
        print(f"  {i+1}. {r['main_id']} (otype={r['otype']}, BH={r['is_bh_candidate']})")
    
    print(f"\n[STATS] Total: {len(unique)}")
    print(f"[STATS] Likely BH: {sum(1 for r in unique if r['is_bh_candidate'])}")

if __name__ == "__main__":
    main()
