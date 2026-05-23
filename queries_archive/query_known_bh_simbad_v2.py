"""
query_known_bh_simbad_v2.py - Query Simbad for known black hole X-ray binaries (fixed)
=========================================================================================
Fix: use correct VOTable field names ("coordinates" not "coords")

Author: math-science workspace / BlackHole Beacon project
Date: 2026-05-23
"""

import json
import time
from pathlib import Path

try:
    from astroquery.simbad import Simbad
    HAS_SIMBAD = True
except ImportError:
    HAS_SIMBAD = False
    print("[WARN] astroquery not installed. Install: pip install astroquery")

def query_known_bh_simbad_v2():
    if not HAS_SIMBAD:
        print("[ERROR] astroquery not available. Cannot query Simbad.")
        return None
    
    # Load known BH list
    input_path = Path(__file__).parent.parent / "data" / "known_bh_xray_binaries.json"
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"[INFO] Loaded {len(data['black_holes'])} known black holes")
    
    # Query Simbad for each
    updated_bh = []
    for i, bh in enumerate(data["black_holes"]):
        name = bh["name"]
        ra = bh["ra_deg"]
        dec = bh["dec_deg"]
        
        print(f"[{i+1}/{len(data['black_holes'])}] Querying Simbad: {name}...")
        
        try:
            # Query by object name
            Simbad.reset_votable_fields()
            # Correct field names: otype, coordinates, ids
            Simbad.add_votable_fields("otype", "coordinates", "ids")
            result = Simbad.query_object(name)
            
            if result is not None and len(result) > 0:
                main_id = result["MAIN_ID"][0]
                otype = result["OTYPE"][0] if "OTYPE" in result.colnames else "Unknown"
                
                # Coordinates are in degrees (decimal degrees)
                ra_simbad = float(result["RA"][0])   # already in degrees
                dec_simbad = float(result["DEC"][0]) # already in degrees
                
                bh["simbad_main_id"] = main_id
                bh["simbad_otype"] = otype
                bh["simbad_ra_deg"] = ra_simbad
                bh["simbad_dec_deg"] = dec_simbad
                bh["query_status"] = "OK"
                
                print(f"  [OK] {name} -> {main_id} (type: {otype})")
            else:
                # Try query by coordinates
                print(f"  [WARN] {name} not found by name, trying coordinates...")
                # Simbad.query_region expects "RA DEC" in degrees
                coord_str = f"{ra} {dec}"
                result2 = Simbad.query_region(coord_str, radius="5m")
                if result2 is not None and len(result2) > 0:
                    # Take closest source
                    main_id2 = result2["MAIN_ID"][0]
                    otype2 = result2["OTYPE"][0] if "OTYPE" in result2.colnames else "Unknown"
                    bh["simbad_main_id"] = main_id2
                    bh["simbad_otype"] = otype2
                    bh["query_status"] = "OK_by_coord"
                    print(f"  [OK] {name} -> {main_id2} (type: {otype2}) [by coord]")
                else:
                    bh["query_status"] = "NOT_FOUND"
                    print(f"  [ERROR] {name} not found in Simbad")
        
        except Exception as e:
            bh["query_status"] = f"ERROR: {str(e)}"
            print(f"  [ERROR] Query failed for {name}: {e}")
        
        updated_bh.append(bh)
        
        # Rate limiting: don't hammer Simbad
        time.sleep(0.5)
    
    # Save updated data
    output_path = Path(__file__).parent.parent / "data" / "known_bh_xray_binaries_simbad_v2.json"
    data["black_holes"] = updated_bh
    data["metadata"]["simbad_query_date"] = time.strftime("%Y-%m-%d")
    data["metadata"]["simbad_query_status"] = f"{sum(1 for bh in updated_bh if 'OK' in bh.get('query_status', ''))}/{len(updated_bh)} OK"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Saved updated data to: {output_path}")
    print(f"[STATS] Success: {sum(1 for bh in updated_bh if 'OK' in bh.get('query_status', ''))}/{len(updated_bh)}")
    return output_path

if __name__ == "__main__":
    query_known_bh_simbad_v2()
