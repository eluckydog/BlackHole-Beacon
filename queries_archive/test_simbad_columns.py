"""
Test Simbad TAP: get actual column names of 'basic' table
"""

from astroquery.simbad import Simbad

print("Testing Simbad TAP: get column names of 'basic' table...")
print("="*70)

# Query TOP 1 QSO, SELECT * to see all column names
print("\nQuery: SELECT TOP 1 * FROM basic WHERE otype='QSO'")
print("  (to see all column names)\n")

try:
    adql = """
    SELECT TOP 1 *
    FROM basic
    WHERE otype='QSO'
    """
    
    result = Simbad.query_tap(adql.strip())
    
    if result is not None and len(result) > 0:
        print(f"  [OK] Got {len(result)} row(s)")
        print(f"  Column names ({len(result.colnames)}): {result.colnames}")
        print(f"\n  First row (all columns):")
        for col in result.colnames:
            val = result[col][0]
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            print(f"    {col}: {val}")
    else:
        print("  [EMPTY] No results")
        
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "="*70)
print("Test completed.")
