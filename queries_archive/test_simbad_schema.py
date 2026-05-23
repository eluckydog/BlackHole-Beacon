"""
Test Simbad TAP schema - find correct column names
"""

import json
from astroquery.simbad import Simbad

print("Testing Simbad TAP schema...")
print("="*60)

# 1. Test a simple query to see column names
print("\n1. Simple test query (TOP 5 QSO)...")
try:
    adql = """
    SELECT TOP 5
        main_id, ra, dec, pmra, pmdec, plx
    FROM basic
    WHERE otype='QSO'
    """
    
    result = Simbad.query_tap(adql.strip())
    
    if result is not None and len(result) > 0:
        print(f"  [OK] Got {len(result)} rows")
        print(f"  Column names: {result.colnames}")
        print(f"  First row: {result[0]}")
    else:
        print("  [EMPTY] No results")
        
except Exception as e:
    print(f"  [ERROR] {e}")

# 2. Test otype list (what otype codes are available?)
print("\n2. Test otype codes...")
test_otypes = ["QSO", "AGN", "WD*", "BD*", "Y*O", "ABG*", "CV*", "Er*"]

for ot in test_otypes:
    try:
        adql = f"""
        SELECT TOP 5
            main_id, otype
        FROM basic
        WHERE otype LIKE '{ot}'
        """
        
        result = Simbad.query_tap(adql.strip())
        
        if result is not None and len(result) > 0:
            print(f"  [OK] otype='{ot}': {len(result)} rows (sample: {result['main_id'][0]})")
        else:
            print(f"  [EMPTY] otype='{ot}': no results")
            
    except Exception as e:
        print(f"  [ERROR] otype='{ot}': {e}")

print("\n" + "="*60)
print("Test completed.")
