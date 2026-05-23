"""
check_phase3_structure.py - Check structure of phase3_candidates_full.json
===================================================================================
Print keys of first candidate to understand data format.
"""

import json
from pathlib import Path

def check_phase3_structure():
    input_path = Path(__file__).parent.parent / "data" / "phase3_candidates_full.json"
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"Total candidates: {len(data)}")
    print(f"\nKeys in first candidate:")
    first = data[0]
    for key in first.keys():
        val = first[key]
        val_type = type(val).__name__
        val_preview = str(val)[:50] if val is not None else "None"
        print(f"  {key}: {val_type} = {val_preview}...")
    
    # Check if 'features' field exists
    if "features" in first:
        print(f"\n'features' field exists! Contents:")
        feat = first["features"]
        for k, v in feat.items():
            print(f"  {k}: {v}")
    else:
        print(f"\n'features' field NOT found in first candidate")
        print(f"Available keys: {list(first.keys())}")

if __name__ == "__main__":
    check_phase3_structure()
