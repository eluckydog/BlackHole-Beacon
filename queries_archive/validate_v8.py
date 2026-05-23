"""
Validate v8.0 ranking on known pulsars/black holes.

Check if known sources appear in v8.0 TOP 50/100.
If yes -> v8.0 is effective.
If no -> adjust Isolation Forest parameters (contamination).
"""

import json
import os
import numpy as np
from astroquery.simbad import Simbad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

print("BlackHole Beacon — Validate v8.0 on Known Sources")
print("="*80)

# ==========
# 1. Load v8.0 ranking
# ==========
print("\n--- 1. Load v8.0 Ranking ---")

ranking_file = os.path.join(DATA_DIR, "classifier_ranking_v8.json")
with open(ranking_file, "r") as f:
    v8_ranking = json.load(f)

print(f"  Loaded {len(v8_ranking)} candidates")

# Build anchor -> rank mapping
v8_rank = {r["anchor"]: i+1 for i, r in enumerate(v8_ranking)}

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
    if source in v8_rank:
        rank = v8_rank[source]
        prob = v8_ranking[rank-1]["prob"]
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
    print("\n  Source           | v8.0 Rank | Prob    | In TOP 50? | In TOP 100?")
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
    print("    2. v8.0 ranking is NOT effective (known sources ranked low)")

# ==========
# 5. Compare v8.0 vs. v7.0 vs. Phase 3
# ==========
print("\n--- 5. Compare v8.0 vs. v7.0 vs. Phase 3 ---")

# Load v7.0 ranking
v7_file = os.path.join(DATA_DIR, "classifier_ranking_v7.json")
with open(v7_file, "r") as f:
    v7_ranking = json.load(f)

v7_rank = {r["anchor"]: i+1 for i, r in enumerate(v7_ranking)}

# Load Phase 3 candidates
phase3_file = os.path.join(DATA_DIR, "phase3_candidates_full.json")
with open(phase3_file, "r") as f:
    phase3_candidates = json.load(f)

phase3_ranking = sorted(
    phase3_candidates,
    key=lambda x: x.get("scores", {}).get("total", 0.0),
    reverse=True
)

phase3_rank = {c.get("anchor", "UNK"): i+1 for i, c in enumerate(phase3_ranking)}

# Compare TOP 1
print(f"\n  TOP 1 Comparison:")
print(f"    v8.0:      {v8_ranking[0]['anchor']} (prob={v8_ranking[0]['prob']:.4f})")
print(f"    v7.0:      {v7_ranking[0]['anchor']} (prob={v7_ranking[0]['prob']:.4f})")
print(f"    Phase 3:    {phase3_ranking[0].get('anchor', 'UNK')} (score={phase3_ranking[0].get('scores', {}).get('total', 0.0):.1f})")

# Overlap analysis
v8_top50 = set(r["anchor"] for r in v8_ranking[:50])
v7_top50 = set(r["anchor"] for r in v7_ranking[:50])
p3_top50 = set(c.get("anchor", "UNK") for c in phase3_ranking[:50])

overlap_v8_v7 = v8_top50 & v7_top50
overlap_v8_p3 = v8_top50 & p3_top50
overlap_v7_p3 = v7_top50 & p3_top50

print(f"\n  TOP 50 Overlap:")
print(f"    v8.0 & v7.0: {len(overlap_v8_v7)} ({len(overlap_v8_v7)/50*100:.1f}%)")
print(f"    v8.0 & Phase 3: {len(overlap_v8_p3)} ({len(overlap_v8_p3)/50*100:.1f}%)")
print(f"    v7.0 & Phase 3: {len(overlap_v7_p3)} ({len(overlap_v7_p3)/50*100:.1f}%)")

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
  2. v8.0 ranking is NOT effective (known sources ranked low)
  
  NEXT STEP:
  - Check Simbad for known pulsars in our search region
  - If known sources are in candidates but ranked LOW -> adjust contamination parameter
  - If known sources are NOT in candidates -> expand search region
""")
elif in_top50 / len(found) >= 0.5:
    print("""
  v8.0 is EFFECTIVE!
  {}% of known sources are in TOP 50.
  
  NEXT STEP:
  - Use v8.0 ranking to select targets for observation
  - Validate TOP 10 anomalies with IR images (2MASS/WISE)
""".format(in_top50/len(found)*100))
else:
    print("""
  v8.0 may need adjustment.
  Only {}% of known sources are in TOP 50.
  
  NEXT STEP:
  - Adjust Isolation Forest contamination parameter
  - Try contamination = 0.05 (5% anomalies) or 0.20 (20% anomalies)
""".format(in_top50/len(found)*100))

print("="*80)
print("DONE. Validation complete.")
print("="*80)
