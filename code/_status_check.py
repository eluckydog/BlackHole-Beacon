import json, os

DATA_DIR = 'data'

# Batch results
with open(os.path.join(DATA_DIR, 'batch_all_results.json')) as f:
    data = json.load(f)
total = len(data)
success = sum(1 for d in data if d.get('matches', {}).get('2mass') or d.get('matches', {}).get('wise'))
empty = total - success
print(f"Batch total: {total}, success: {success}, empty: {empty}")

# Checkpoint
cp = os.path.join(DATA_DIR, '_checkpoint.json')
if os.path.exists(cp):
    with open(cp) as f:
        cpdata = json.load(f)
    print(f"Checkpoint idx: {cpdata.get('last_anchor_idx', '?')}")
    print(f"Status: {cpdata.get('status', '?')}")

# Phase3 candidates
p3 = os.path.join(DATA_DIR, 'phase3_candidates_full.json')
if os.path.exists(p3):
    with open(p3) as f:
        p3data = json.load(f)
    print(f"Phase3 candidates: {len(p3data)}")

# Classifier ranking
cr = os.path.join(DATA_DIR, 'classifier_ranking_v2.json')
if os.path.exists(cr):
    with open(cr) as f:
        crdata = json.load(f)
    print(f"Classifier ranked: {len(crdata)}")
