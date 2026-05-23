"""
Check TOP 10 anomalies on Simbad (via astroquery).
"""

import json
import os
from astroquery.simbad import Simbad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

# Load v7.0 ranking
ranking_file = os.path.join(DATA_DIR, "classifier_ranking_v7.json")
with open(ranking_file, "r") as f:
    ranking = json.load(f)

# TOP 10
top10 = ranking[:10]

print("Checking TOP 10 anomalies on Simbad...")
print("="*80)

for i, r in enumerate(top10):
    anchor = r["anchor"]
    print(f"\n{i+1}. {anchor} (anomaly_score={r['anomaly_score']:.4f}, prob={r['prob']:.4f})")
    
    try:
        # Query Simbad by identifier
        result = Simbad.query_object(anchor, verbose=False)
        
        if result is not None and len(result) > 0:
            print(f"  FOUND on Simbad!")
            print(f"  Main ID: {result['MAIN_ID'][0]}")
            print(f"  Type: {result['OTYPE'][0] if 'OTYPE' in result.columns else 'N/A'}")
            print(f"  RA: {result['RA'][0]}")
            print(f"  DEC: {result['DEC'][0]}")
        else:
            print(f"  NOT FOUND on Simbad")
    
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "="*80)
print("DONE. Check complete.")
print("="*80)
