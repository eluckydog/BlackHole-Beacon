#!/usr/bin/env python3
"""
Retry fetching IR colors for remaining 7 BlackCAT sources.
Use larger search radius (20 arcsec) and query both 2MASS & WISE together.
"""

import os
import json
import astroquery
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
from astropy import units as u

def load_missing_sources(json_path="data/known_bh_xray_binaries_features_v2.json"):
    """Load BlackCAT sources that don't have features."""
    print(f"[INFO] Loading: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter to only those without features
    missing = [bh for bh in data["black_holes"] if not bh.get("has_features", False)]
    
    print(f"[INFO] Total BlackCAT sources: {len(data['black_holes'])}")
    print(f"[INFO] With features: {len(data['black_holes']) - len(missing)}")
    print(f"[INFO] Without features: {len(missing)}")
    
    for bh in missing:
        print(f"[INFO]   - {bh['name']} ({bh.get('simbad_main_id', 'Unknown')})")
    
    return missing, data

def query_2mass_wise_combined(ra_deg, dec_deg, radius_arcsec=20.0):
    """Query both 2MASS and WISE catalogs via VizieR."""
    try:
        # Convert to SkyCoord
        coord = SkyCoord(ra_deg, dec_deg, unit='deg', frame='icrs')
        
        # Query 2MASS (catalog II/246)
        vizier = Vizier(columns=['_RAJ2000', '_DEJ2000', 'Jmag', 'Hmag', 'Kmag'])
        vizier.ROW_LIMIT = 20
        
        result_2mass = vizier.query_region(
            coord,
            radius=radius_arcsec * u.arcsec,
            catalog='II/246'
        )
        
        # Query WISE (catalog II/328)
        vizier_cols = Vizier(columns=['_RAJ2000', '_DEJ2000', 'W1mag', 'W2mag', 'W3mag'])
        vizier_cols.ROW_LIMIT = 20
        
        result_wise = vizier_cols.query_region(
            coord,
            radius=radius_arcsec * u.arcsec,
            catalog='II/328'
        )
        
        features = {}
        
        # Parse 2MASS result
        if result_2mass and len(result_2mass) > 0 and len(result_2mass[0]) > 0:
            row = result_2mass[0][0]  # First match
            features['J_mag'] = float(row['Jmag']) if row['Jmag'] else None
            features['H_mag'] = float(row['Hmag']) if row['Hmag'] else None
            features['K_mag'] = float(row['Kmag']) if row['Kmag'] else None
            print(f"[OK]   2MASS: J={features['J_mag']}, H={features['H_mag']}, K={features['K_mag']}")
        
        # Parse WISE result
        if result_wise and len(result_wise) > 0 and len(result_wise[0]) > 0:
            row = result_wise[0][0]  # First match
            features['W1_mag'] = float(row['W1mag']) if row['W1mag'] else None
            features['W2_mag'] = float(row['W2mag']) if row['W2mag'] else None
            features['W3_mag'] = float(row['W3mag']) if row['W3mag'] else None
            print(f"[OK]   WISE: W1={features['W1_mag']}, W2={features['W2_mag']}, W3={features['W3_mag']}")
        
        # Calculate colors if we have enough magnitudes
        if all(k in features for k in ['J_mag', 'H_mag', 'K_mag', 'W1_mag', 'W2_mag', 'W3_mag']):
            features['J-H'] = features['J_mag'] - features['H_mag']
            features['H-K'] = features['H_mag'] - features['K_mag']
            features['W1-W2'] = features['W1_mag'] - features['W2_mag']
            features['W2-W3'] = features['W2_mag'] - features['W3_mag']
            features['pm_ra'] = None
            features['pm_dec'] = None
            features['pm_total'] = None
            return features
        
        # Partial features (only 2MASS or only WISE)
        if 'J_mag' in features and 'H_mag' in features and 'K_mag' in features:
            features['J-H'] = features['J_mag'] - features['H_mag']
            features['H-K'] = features['H_mag'] - features['K_mag']
        
        if 'W1_mag' in features and 'W2_mag' in features and 'W3_mag' in features:
            features['W1-W2'] = features['W1_mag'] - features['W2_mag']
            features['W2-W3'] = features['W2_mag'] - features['W3_mag']
        
        if 'J_mag' in features or 'W1_mag' in features:
            features['pm_ra'] = None
            features['pm_dec'] = None
            features['pm_total'] = None
            return features  # Return partial features
        
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        pass  # Silent fail
    
    return None

def update_json_with_features(json_path, bh_name, features):
    """Update JSON file with new features."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Find the black hole and update
    for bh in data['black_holes']:
        if bh['name'] == bh_name:
            bh['features'] = features
            bh['has_features'] = True
            bh['query_status'] = 'OK_retry_v4'
            break
    
    # Update metadata
    with_features = sum(1 for bh in data['black_holes'] if bh.get('has_features', False))
    data['metadata']['feature_query_status'] = f"{with_features}/{len(data['black_holes'])} with features"
    data['metadata']['feature_query_date'] = "2026-05-23_retry_v4"
    
    # Save
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Updated {json_path} ({with_features}/{len(data['black_holes'])} with features)")

def main():
    print("=" * 60)
    print("BlackCAT - Retry IR Color Query (v4, 20 arcsec)")
    print("=" * 60)
    
    # Step 1: Load missing sources
    missing_sources, data = load_missing_sources(
        json_path="data/known_bh_xray_binaries_features_v2.json"
    )
    
    if not missing_sources:
        print("[INFO] All sources already have features!")
        return
    
    # Step 2: Query IR colors for each missing source
    json_path = "data/known_bh_xray_binaries_features_v2.json"
    success_count = 0
    
    for bh in missing_sources:
        ra = bh.get('simbad_ra_deg') or bh.get('ra_deg')
        dec = bh.get('simbad_dec_deg') or bh.get('dec_deg')
        
        if not ra or not dec:
            print(f"[WARN] No coordinates for {bh['name']}")
            continue
        
        print(f"\n[INFO] Querying IR colors for {bh['name']} at RA={ra:.4f}, Dec={dec:.4f}")
        
        features = query_2mass_wise_combined(ra, dec, radius_arcsec=20.0)
        
        if features:
            update_json_with_features(json_path, bh['name'], features)
            success_count += 1
        else:
            print(f"[ERROR] Failed to query IR colors for {bh['name']}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Missing sources: {len(missing_sources)}")
    print(f"Successfully queried: {success_count}")
    print(f"Still missing: {len(missing_sources) - success_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
