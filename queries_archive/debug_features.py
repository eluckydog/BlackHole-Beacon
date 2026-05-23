"""Debug feature extraction for BlackHole Beacon classifier."""

import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

print("Debugging BlackHole Beacon feature extraction")
print("="*60)

# ==============================
# 1. Inspect batch_all_results.json
# ==============================
print("\n--- 1. batch_all_results.json ---")
with open(os.path.join(DATA_DIR, "batch_all_results.json")) as f:
    batch = json.load(f)

print(f"Total entries: {len(batch)}")
if batch:
    print(f"First entry keys: {list(batch[0].keys())}")
    print("First entry (truncated):")
    import pprint
    pprint.pprint(batch[0], depth=2)

# ==============================
# 2. Inspect phase3_candidates.json
# ==============================
print("\n--- 2. phase3_candidates.json ---")
with open(os.path.join(DATA_DIR, "phase3_candidates.json")) as f:
    phase3 = json.load(f)

print(f"Total entries: {len(phase3)}")
if phase3:
    print(f"First entry keys: {list(phase3[0].keys())}")
    print("First entry (truncated):")
    pprint.pprint(phase3[0], depth=2)

# ==============================
# 3. Check name matching
# ==============================
print("\n--- 3. Name Matching Check ---")
batch_names = set()
for a in batch[:20]:  # Check first 20
    n = a.get("anchor") or a.get("name") or ""
    batch_names.add(n)

phase3_names = set()
for c in phase3[:20]:
    n = c.get("anchor") or c.get("name") or ""
    phase3_names.add(n)

print(f"Batch names (first 20): {batch_names}")
print(f"Phase3 names (first 20): {phase3_names}")
print(f"Overlap: {batch_names & phase3_names}")

# ==============================
# 4. Test feature extraction
# ==============================
print("\n--- 4. Test Feature Extraction ---")
sys_path = os.path.join(ROOT, "queries", "classifier_train.py")
# Import the extract_features function
import sys
sys.path.insert(0, os.path.join(ROOT, "queries"))
try:
    from classifier_train import extract_features
    print("Imported extract_features OK")
    
    # Test with first batch entry
    if batch:
        test_anchor = batch[0].get("anchor") or batch[0].get("name") or "TEST"
        test_match = batch[0].get("matches", {})
        print(f"\nTest anchor: {test_anchor}")
        print(f"Test match keys: {list(test_match.keys()) if test_match else 'EMPTY'}")
        feats = extract_features(test_anchor, test_match)
        print(f"Extracted features: {feats}")
except Exception as e:
    print(f"Import/execution error: {e}")
    import traceback
    traceback.print_exc()

print("\nDone.")
