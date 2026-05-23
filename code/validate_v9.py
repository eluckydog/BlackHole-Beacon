"""Validate v9.0 ranking using known pulsars/black holes."""
import json, os
from astroquery.simbad import Simbad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V9 = os.path.join(ROOT, "data", "classifier_ranking_v9.json")

# Known pulsars (from ATNF catalog or literature)
KNOWN = [
    "J0419+4404",  # PSR J0419+4404
    "J0534+2200",  # Crab pulsar
    "J0834-4159",  # PSR J0834-4159
    "J1107-6143",  # PSR J1107-6143
    "J1119-6127",  # PSR J1119-6127
    "J1822-4209",  # PSR J1822-4209
    "J1823-3021D", # PSR J1823-3021D
    "J1824-2452A", # PSR J1824-2452A
    "J1833-1035",  # PSR J1833-1035
    "J1913+1011",  # PSR J1913+1011
]

print("BlackHole Beacon — Validate v9.0 Ranking")
print("="*80)

# Load v9.0 ranking
with open(V9, "r") as f:
    v9 = json.load(f)

print(f"\n--- 1. Check Known Pulsars in v9.0 Ranking ---")
print(f"  Total candidates: {len(v9)}")

found = []
for i, r in enumerate(v9):
    anchor = r.get("anchor", "")
    if anchor in KNOWN:
        found.append((i+1, anchor, r["prob"]))
        print(f"  FOUND: {anchor} at rank {i+1} (prob={r['prob']:.4f})")

if not found:
    print("  NONE of the known pulsars are in the v9.0 ranking (top 2455).")
else:
    print(f"\n  Found {len(found)} / {len(KNOWN)} known pulsars.")
    for rank, anchor, prob in found:
        print(f"    Rank {rank}: {anchor} (prob={prob:.4f})")

# Check TOP 50/100
print(f"\n--- 2. Check TOP 50/100 ---")
top50 = [r["anchor"] for r in v9[:50]]
top100 = [r["anchor"] for r in v9[:100]]

found_top50 = [p for p in KNOWN if p in top50]
found_top100 = [p for p in KNOWN if p in top100]

print(f"  Known in TOP 50:  {len(found_top50)} / {len(KNOWN)}")
print(f"  Known in TOP 100: {len(found_top100)} / {len(KNOWN)}")

if found_top50:
    print(f"    TOP 50: {found_top50}")
if found_top100:
    print(f"    TOP 100: {found_top100}")

# Summary
print(f"\n" + "="*80)
print("SUMMARY:")
print(f"  v9.0 Validation Result:")
if found_top50:
    print(f"    [OK] KNOWN PULSARS IN TOP 50 → v9.0 is EFFECTIVE")
elif found_top100:
    print(f"    [!!] KNOWN PULSARS IN TOP 100 → v9.0 is PARTIALLY EFFECTIVE")
else:
    print(f"    [NO] NO KNOWN PULSARS IN TOP 100 → v9.0 is INEFFECTIVE")

print(f"\n  Next steps:")
if found_top50:
    print(f"    1. Prepare observation proposal for TOP 10 anomalies")
    print(f"    2. Cross-match TOP 10 with X-ray/radio catalogs")
else:
    print(f"    1. Adjust Isolation Forest parameters (contamination)")
    print(f"    2. Try other feature combinations (e.g., only IR colors)")
    print(f"    3. Collect more real negative samples")

print("="*80)
