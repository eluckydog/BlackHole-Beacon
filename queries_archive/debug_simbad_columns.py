"""
debug_simbad_columns.py - Debug Simbad query result columns
===================================================================
Run a single test query to see what columns are returned.

Author: math-science workspace / BlackHole Beacon project
Date: 2026-05-23
"""

import json
from pathlib import Path

try:
    from astroquery.simbad import Simbad
    HAS_SIMBAD = True
except ImportError:
    HAS_SIMBAD = False
    print("[ERROR] astroquery not installed")

def debug_simbad_columns():
    if not HAS_SIMBAD:
        return
    
    # Test query for Cyg X-1
    test_name = "Cyg X-1"
    
    print(f"[DEBUG] Querying Simbad for: {test_name}")
    
    try:
        # Reset and add fields
        Simbad.reset_votable_fields()
        Simbad.add_votable_fields("otype", "coordinates", "ids")
        
        result = Simbad.query_object(test_name)
        
        if result is not None and len(result) > 0:
            print(f"[DEBUG] Query succeeded! Result has {len(result)} rows")
            print(f"[DEBUG] Column names: {result.colnames}")
            print(f"[DEBUG] First row:")
            for col in result.colnames:
                print(f"  {col}: {result[col][0]}")
        else:
            print(f"[DEBUG] Query returned None or empty result")
            
            # Try TAP query instead
            print(f"[DEBUG] Trying TAP query...")
            from astroquery.simbad import Simbad as SimbadTAP
            # TAP interface
            tap = SimbadTAP()
            # ... (will implement if needed)
    
    except Exception as e:
        print(f"[DEBUG] Query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_simbad_columns()
