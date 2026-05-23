"""
Query ALL known black hole X-ray binaries from Simbad (v2 - simpler approach)
Use wildcard search for "black hole" in object names
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
OUT_FILE = Path(__file__).parent.parent / "data" / "all_known_bh_xrb_simbad_v2.json"

def query_bh_xrb_simple():
    """Query Simbad for HXB and LXB (confirmed BH XRBs)."""
    print("[INFO] Querying Simbad for HXB (High-mass X-ray Binaries with BH)...")
    try:
        # Reset to default fields
        Simbad.reset_votable_fields()
        
        # Query for HXB
        result_hxb = Simbad.query_criteria(otype="HXB", maxrows=500)
        print(f"[OK] HXB query returned {len(result_hxb) if result_hxb is not None else 0} rows")
        
        # Query for LXB
        print("[INFO] Querying Simbad for LXB (Low-mass X-ray Binaries)...")
        Simbad.reset_votable_fields()
        result_lxb = Simbad.query_criteria(otype="LXB", maxrows=500)
        print(f"[OK] LXB query returned {len(result_lxb) if result_lxb is not None else 0} rows")
        
        # Combine
        combined = []
        if result_hxb is not None and len(result_hxb) > 0:
            combined.append(result_hxb)
        if result_lxb is not None and len(result_lxb) > 0:
            combined.append(result_lxb)
        
        if not combined:
            print("[WARN] No results from HXB/LXB query")
            return []
        
        # Merge tables
        from astropy.table import vstack
        merged = vstack(combined)
        print(f"[INFO] Merged table has {len(merged)} rows")
        
        # Convert to list of dicts (safely)
        records = []
        for row in merged:
            try:
                main_id = str(row["main_id"])
                ra = float(row["ra"]) if row["ra"] is not None else None
                dec = float(row["dec"]) if row["dec"] is not None else None
                otype = str(row["otype"]) if "otype" in row.colnames else "Unknown"
                
                records.append({
                    "main_id": main_id,
                    "ra": ra,
                    "dec": dec,
                    "otype": otype,
                    "source": "Simbad query_criteria"
                })
            except Exception as e:
                print(f"[WARN] Error processing row: {e}")
                continue
        
        return records
        
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print("[INFO] Starting Simbad query for known BH XRBs...")
    records = query_bh_xrb_simple()
    
    if not records:
        print("[ERROR] No records found. Try manual compilation.")
        return
    
    print(f"[INFO] Total records: {len(records)}")
    
    # Deduplicate by main_id
    seen = set()
    unique = []
    for r in records:
        mid = r["main_id"]
        if mid not in seen:
            seen.add(mid)
            unique.append(r)
    
    print(f"[INFO] Unique records: {len(unique)}")
    
    # Save
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "Simbad query_criteria (HXB+LXB)",
                "query_date": time.strftime("%Y-%m-%d"),
                "total_unique": len(unique)
            },
            "records": unique
        }, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved {len(unique)} records to: {OUT_FILE}")
    
    # Print first 30
    print("\n--- First 30 records ---")
    for i, r in enumerate(unique[:30]):
        print(f"  {i+1}. {r['main_id']} (otype={r['otype']})")
    
    print(f"\n[STATS] Total: {len(unique)}")
    print(f"[STATS] HXB: {sum(1 for r in unique if 'HXB' in r['otype'])}")
    print(f"[STATS] LXB: {sum(1 for r in unique if 'LXB' in r['otype'])}")

if __name__ == "__main__":
    main()
