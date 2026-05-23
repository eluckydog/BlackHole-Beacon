"""
Query BlackCAT catalog (J/ApJ/813/L5) from VizieR
Use astroquery.vizier to get the full 59 entries.
"""
import sys
import json
import time
from pathlib import Path

try:
    from astroquery.vizier import Vizier
    from astropy.table import Table
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Install: pip install astroquery astropy")
    sys.exit(1)

# -- Output file --
OUT_FILE = Path(__file__).parent.parent / "data" / "blackcat_vizier.json"

def query_blackcat():
    """Query VizieR for BlackCAT catalog."""
    print("[INFO] Querying VizieR for BlackCAT catalog (J/ApJ/813/L5)...")
    
    try:
        # BlackCAT catalog identifier
        catalog_id = "J/ApJ/813/L5"
        
        # Query with large row limit
        Vizier.ROW_LIMIT = 100
        catalogs = Vizier.get_catalogs(catalog_id)
        
        if not catalogs:
            print("[ERROR] No catalogs found")
            return []
        
        print(f"[OK] Got {len(catalogs)} table(s)")
        
        # Combine all tables
        combined = Table()
        for cat in catalogs:
            if len(cat) > 0:
                if len(combined) == 0:
                    combined = cat
                else:
                    combined = Table(vstack([combined, cat]))
        
        print(f"[INFO] Combined table has {len(combined)} rows")
        
        # Convert to list of dicts
        records = []
        for row in combined:
            try:
                record = {}
                for col in combined.colnames:
                    val = row[col]
                    if val is None:
                        record[col] = None
                    else:
                        record[col] = val
                records.append(record)
            except Exception as e:
                print(f"[WARN] Error processing row: {e}")
                continue
        
        return records
        
    except Exception as e:
        print(f"[ERROR] VizieR query failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print("[INFO] Starting BlackCAT catalog query...")
    records = query_blackcat()
    
    if not records:
        print("[ERROR] No records found. Try manual compilation.")
        return
    
    print(f"[INFO] Total records: {len(records)}")
    
    # Save
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "VizieR J/ApJ/813/L5 (BlackCAT)",
                "query_date": time.strftime("%Y-%m-%d"),
                "total_entries": len(records)
            },
            "records": records
        }, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved {len(records)} records to: {OUT_FILE}")
    
    # Print first 20
    print("\n--- First 20 records ---")
    for i, r in enumerate(records[:20]):
        # Print first few keys
        keys = list(r.keys())[:5]
        vals = [r[k] for k in keys]
        print(f"  {i+1}. {keys} = {vals}")
    
    print(f"\n[STATS] Total: {len(records)}")

if __name__ == "__main__":
    main()
