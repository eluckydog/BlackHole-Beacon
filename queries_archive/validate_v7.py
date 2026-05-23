"""
Validate v7.0 ranking on known pulsars/black holes.

Check if known sources appear in v7.0 TOP 50/100.
If yes -> v7.0 is effective.
If no -> adjust Isolation Forest parameters (contamination).
"""

import json
import os
import numpy as np
from astroquery.simbad import Simbad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

print("BlackHole Beacon — Validate v7.0 on Known Sources")
print("="*80)

# ==========
# 1. Load v7.0 ranking
# ==========
print("\n--- 1. Load v7.0 Ranking ---")

ranking_file = os.path.join(DATA_DIR, "classifier_ranking_v7.json")
with open(ranking_file, "r") as f:
    v7_ranking = json.load(f)

print(f"  Loaded {len(v7_ranking)} candidates")

# Build anchor -> rank mapping
v7_rank = {r["anchor"]: i+1 for i, r in enumerate(v7_ranking)}

# ==========
# 2. Known pulsars/black holes (test set)
# ==========
print("\n--- 2. Known Pulsars/Black Holes (Test Set) ---")

# Hand-curated list of known pulsars/black holes
# These are famous sources that SHOULD be in our candidates
known_sources = [
    # Pulsars (high PM, known in SIMBAD)
    "J1939+2134",  # PSR B1937+21 (fastest known pulsar)
    "J0534+2200",  # Crab Pulsar (M1)
    "J0835-4510",  # Vela Pulsar
    "J0633+1746",  # Geminga (middle-aged pulsar)
    "J0659+1414",  # PSR B0656+14
    "J0834+0609",  # PSR J0834+0609
    "J1024-0719",  # PSR J1024-0719
    "J1045-4509",  # PSR J1045-4509
    "J1456-6843",  # PSR J1456-6843
    "J1744-1134",  # PSR J1744-1134
    
    # Black hole candidates (X-ray binaries)
    "J1655-404",   # GRO J1655-40 (black hole candidate)
    "J1550-564",   # GRO J1550-56 (black hole candidate)
    "J1124-6839",  # GRO J1124-68 (black hole candidate)
]

print(f"  Test set: {len(known_sources)} known sources")

# ==========
# 3. Check if known sources are in our candidates
# ==========
print("\n--- 3. Check if Known Sources are in Candidates ---")

found = []
not_found = []

for source in known_sources:
    if source in v7_rank:
        rank = v7_rank[source]
        prob = v7_ranking[rank-1]["prob"]
        found.append((source, rank, prob))
    else:
        not_found.append(source)

print(f"  Found: {len(found)} / {len(known_sources)}")
print(f"  Not found: {len(not_found)} / {len(known_sources)}")

# ==========
# 4. Analyze ranking of found sources
# ==========
print("\n--- 4. Ranking of Found Sources ---")

if len(found) > 0:
    print("\n  Source           | v7.0 Rank | Prob    | In TOP 50? | In TOP 100?")
    print("  " + "-"*70)
    
    in_top50 = 0
    in_top100 = 0
    
    for source, rank, prob in found:
        top50 = "YES" if rank <= 50 else "NO"
        top100 = "YES" if rank <= 100 else "NO"
        
        if rank <= 50:
            in_top50 += 1
        if rank <= 100:
            in_top100 += 1
        
        print(f"  {source:15s} | {rank:10d} | {prob:.4f} | {top50:9s} | {top100:10s}")
    
    print(f"\n  Summary:")
    print(f"    In TOP 50: {in_top50} / {len(found)} ({in_top50/len(found)*100:.1f}%)")
    print(f"    In TOP 100: {in_top100} / {len(found)} ({in_top100/len(found)*100:.1f}%)")
else:
    print("\n  WARNING: NO known sources found in candidates!")
    print("  This means EITHER:")
    print("    1. Our candidates do NOT include known pulsars/BH")
    print("    2. v7.0 ranking is NOT effective (known sources ranked low)")

# ==========
# 5. Check NOT FOUND sources on Simbad
# ==========
print("\n--- 5. Check NOT FOUND Sources on Simbad ---")

if len(not_found) > 0:
    print(f"\n  Checking {len(not_found)} NOT FOUND sources on Simbad...")
    
    for source in not_found[:5]:  # Check first 5 only
        print(f"\n    {source}:")
        try:
            result = Simbad.query_object(source, verbose=False)
            if result is not None and len(result) > 0:
                main_id = result['MAIN_ID'][0]
                otype = result['OTYPE'][0] if 'OTYPE' in result.columns else 'N/A'
                print(f"      FOUND on Simbad: {main_id} (type: {otype})")
            else:
                print(f"      NOT FOUND on Simbad")
        except Exception as e:
            print(f"      ERROR: {e}")

# ==========
# 6. Conclusion
# ==========
print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

if len(found) == 0:
    print("""
  NO known sources found in candidates.
  
  Possible reasons:
  1. Our candidate list does NOT include known pulsars/BH
  2. v7.0 ranking is NOT effective (known sources ranked low)
  
  NEXT STEP:
  - Check Simbad for known pulsars in our search region
  - If known sources are in candidates but ranked LOW -> adjust contamination parameter
  - If known sources are NOT in candidates -> expand search region
""")
elif in_top50 / len(found) >= 0.5:
    print("""
  v7.0 is EFFECTIVE!
  {}% of known sources are in TOP 50.
  
  NEXT STEP:
  - Use v7.0 ranking to select targets for observation
  - Validate TOP 10 anomalies with IR images (2MASS/WISE)
""".format(in_top50/len(found)*100))
else:
    print("""
  v7.0 may need adjustment.
  Only {}% of known sources are in TOP 50.
  
  NEXT STEP:
  - Adjust Isolation Forest contamination parameter
  - Try contamination = 0.05 (5% anomalies) or 0.20 (20% anomalies)
""".format(in_top50/len(found)*100))

print("="*80)
print("DONE. Validation complete.")
print("="*80)
