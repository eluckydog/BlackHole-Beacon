"""
check_features_summary.py - Check which black holes have features
====================================================================
Print summary of known_bh_xray_binaries_features_v2.json
"""

import json
from pathlib import Path

def check_features_summary():
    input_path = Path(__file__).parent.parent / "data" / "known_bh_xray_binaries_features_v2.json"
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"Total black holes: {len(data['black_holes'])}")
    print("\n--- With features (has_features=True) ---")
    
    with_features = []
    without_features = []
    
    for i, bh in enumerate(data["black_holes"]):
        name = bh.get("simbad_main_id", bh["name"])
        has_feat = bh.get("has_features", False)
        
        if has_feat:
            with_features.append((i+1, name))
        else:
            without_features.append((i+1, name))
    
    for idx, name in with_features:
        print(f"  {idx}. {name}")
    
    print(f"\n--- Without features (has_features=False) ---")
    for idx, name in without_features:
        print(f"  {idx}. {name}")
    
    print(f"\nStats: {len(with_features)}/{len(data['black_holes'])} with features")

if __name__ == "__main__":
    check_features_summary()
