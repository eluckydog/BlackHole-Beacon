"""
Inspect TOP 10 anomalies (v8.0) in detail.

Check:
1. IR images (2MASS/WISE) - does it look like a pulsar/BH?
2. X-ray/radio counterparts (from Simbad)
3. PM and variability
"""

import json
import os
from astroquery.simbad import Simbad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

print("BlackHole Beacon — Inspect TOP 10 Anomalies (v8.0)")
print("="*80)

# ==========
# 1. Load v8.0 ranking
# ==========
print("\n--- 1. Load v8.0 Ranking ---")

ranking_file = os.path.join(DATA_DIR, "classifier_ranking_v8.json")
with open(ranking_file, "r") as f:
    ranking = json.load(f)

# TOP 10
top10 = ranking[:10]

print(f"  Loaded {len(ranking)} candidates")
print(f"  TOP 10 anomalies (v8.0):")

for i, r in enumerate(top10):
    print(f"    {i+1}. {r['anchor']} (score={r['anomaly_score']:.4f}, prob={r['prob']:.4f})")

# ==========
# 2. Load candidate details
# ==========
print("\n--- 2. Load Candidate Details ---")

phase3_file = os.path.join(DATA_DIR, "phase3_candidates_full.json")
with open(phase3_file, "r") as f:
    candidates = json.load(f)

# Build anchor -> candidate mapping
candidate_dict = {c.get("anchor", f"UNK_{i}"): c for i, c in enumerate(candidates)}

# ==========
# 3. Inspect each TOP 10 anomaly
# ==========
print("\n--- 3. Inspect TOP 10 Anomalies ---")

for i, r in enumerate(top10):
    anchor = r["anchor"]
    print(f"\n{'='*80}")
    print(f"  {i+1}. {anchor}")
    print(f"{'='*80}")
    
    if anchor not in candidate_dict:
        print(f"  NOT FOUND in phase3_candidates_full.json")
        continue
    
    c = candidate_dict[anchor]
    
    # Basic info
    ra = c.get("ra", 0.0) or 0.0
    dec = c.get("dec", 0.0) or 0.0
    pm = c.get("proper_motion_masyr", 0.0) or 0.0
    
    print(f"  RA: {ra:.4f}")
    print(f"  DEC: {dec:.4f}")
    print(f"  PM: {pm:.1f} mas/yr")
    
    # IR colors
    j = c.get("J", None)
    h = c.get("H", None)
    k = c.get("K", None)
    w1 = c.get("W1", None)
    w2 = c.get("W2", None)
    w3 = c.get("W3", None)
    
    print(f"\n  IR Colors:")
    if j is not None and h is not None:
        print(f"    J-H: {j-h:.3f}")
    if h is not None and k is not None:
        print(f"    H-K: {h-k:.3f}")
    if w1 is not None and w2 is not None:
        print(f"    W1-W2: {w1-w2:.3f}")
    if w2 is not None and w3 is not None:
        print(f"    W2-W3: {w2-w3:.3f}")
    
    # Phase 3 scores
    scores = c.get("scores", {})
    print(f"\n  Phase 3 Scores:")
    print(f"    Total: {scores.get('total', 0.0):.1f}")
    print(f"    Color: {scores.get('color', 0.0):.1f}")
    print(f"    PM: {scores.get('pm', 0.0):.1f}")
    print(f"    Variability: {scores.get('variability', 0.0):.1f}")
    print(f"    Compactness: {scores.get('compactness', 0.0):.1f}")
    
    # Check Simbad for X-ray/radio counterparts
    print(f"\n  Checking Simbad for counterparts...")
    try:
        result = Simbad.query_object(anchor, verbose=False)
        if result is not None and len(result) > 0:
            main_id = result['MAIN_ID'][0]
            otype = result['OTYPE'][0] if 'OTYPE' in result.columns else 'N/A'
            print(f"    FOUND on Simbad: {main_id}")
            print(f"    Type: {otype}")
        else:
            print(f"    NOT FOUND on Simbad")
    except Exception as e:
        print(f"    ERROR: {e}")

# ==========
# 4. Summary
# ==========
print("\n" + "="*80)
print("SUMMARY:")
print("="*80)

print("""
  TOP 10 anomalies (v8.0) inspected.
  
  NEXT STEPS:
  1. Check IR images (2MASS/WISE) for each TOP 10 anomaly
     -> Does it look like a pulsar/BH?
  2. Check X-ray/radio counterparts (from Simbad/NED)
     -> Is it detected in X-ray/radio?
  3. If YES to both -> High priority candidate for observation
  4. If NO -> Likely a false positive (AGN, YSO, etc.)
""")

print("="*80)
print("DONE. Inspection complete.")
print("="*80)
