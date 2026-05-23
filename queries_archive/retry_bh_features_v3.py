#!/usr/bin/env python3
"""
Retry fetching IR colors for BlackCAT sources that failed previously.
Use larger search radius (10 arcsec) and query 2MASS/WISE directly via VizieR.
"""

import os
import json
import astroquery
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
from astropy import units as u
import numpy as np

def load_failed_sources(json_path="data/known_bh_xray_binaries_features_v2.json"):
    """Load BlackCAT sources that don't have features."""
    print(f"[INFO] Loading: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter to only those without features
    failed = [bh for bh in data["black_holes"] if not bh.get("has_features", False)]
    
    print(f"[INFO] Total BlackCAT sources: {len(data['black_holes'])}")
    print(f"[INFO] With features: {len(data['black_holes']) - len(failed)}")
    print(f"[INFO] Without features: {len(failed)}")
    
    for bh in failed:
        print(f"[INFO]   - {bh['name']} ({bh.get('simbad_main_id', 'Unknown')})")
    
    return failed

def query_2mass_vizier(ra_deg, dec_deg, radius_arcsec=10.0):
    """Query 2MASS catalog via VizieR."""
    try:
        # Convert to SkyCoord
        coord = SkyCoord(ra_deg, dec_deg, unit='deg', frame='icrs')
        
        # Query 2MASS (catalog ID: II/246)
        vizier = Vizier(columns=['_RAJ2000', '_DEJ2000', 'Jmag', 'Hmag', 'Kmag'])
        vizier.ROW_LIMIT = 10
        
        result = vizier.query_region(
            coord,
            radius=radius_arcsec * u.arcsec,
            catalog='II/246'
        )
        
        if result and len(result) > 0 and len(result[0]) > 0:
            row = result[0][0]  # First match
            return {
                'J_mag': float(row['Jmag']) if row['Jmag'] else None,
                'H_mag': float(row['Hmag']) if row['Hmag'] else None,
                'K_mag': float(row['Kmag']) if row['Kmag'] else None,
            }
    
    except Exception as e:
        pass  # Silent fail, try WISE
    
    return None

def query_wise_vizier(ra_deg, dec_deg, radius_arcsec=10.0):
    """Query WISE catalog via VizieR."""
    try:
        # Convert to SkyCoord
        coord = SkyCoord(ra_deg, dec_deg, unit='deg', frame='icrs')
        
        # Query WISE (catalog ID: II/328)
        vizier = Vizier(columns=['_RAJ2000', '_DEJ2000', 'W1mag', 'W2mag', 'W3mag'])
        vizier.ROW_LIMIT = 10
        
        result = vizier.query_region(
            coord,
            radius=radius_arcsec * u.arcsec,
            catalog='II/328'
        )
        
        if result and len(result) > 0 and len(result[0]) > 0:
            row = result[0][0]  # First match
            return {
                'W1_mag': float(row['W1mag']) if row['W1mag'] else None,
                'W2_mag': float(row['W2mag']) if row['W2mag'] else None,
                'W3_mag': float(row['W3mag']) if row['W3mag'] else None,
            }
    
    except Exception as e:
        pass  # Silent fail
    
    return None

def query_ir_colors(bh):
    """Query IR colors for a BlackCAT source."""
    ra = bh.get('simbad_ra_deg') or bh.get('ra_deg')
    dec = bh.get('simbad_dec_deg') or bh.get('dec_deg')
    
    if not ra or not dec:
        print(f"[WARN] No coordinates for {bh['name']}")
        return None
    
    print(f"[INFO] Querying IR colors for {bh['name']} at RA={ra:.4f}, Dec={dec:.4f}")
    
    # Try 2MASS
    mass_result = query_2mass_vizier(ra, dec, radius_arcsec=10.0)
    
    # Try WISE
    wise_result = query_wise_vizier(ra, dec, radius_arcsec=10.0)
    
    # Merge results
    features = {}
    if mass_result:
        features.update(mass_result)
        print(f"[OK]   2MASS: J={mass_result.get('J_mag')}, H={mass_result.get('H_mag')}, K={mass_result.get('K_mag')}")
    
    if wise_result:
        features.update(wise_result)
        print(f"[OK]   WISE: W1={wise_result.get('W1_mag')}, W2={wise_result.get('W2_mag')}, W3={wise_result.get('W3_mag')}")
    
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
            bh['query_status'] = 'OK_retry'
            break
    
    # Update metadata
    with_features = sum(1 for bh in data['black_holes'] if bh.get('has_features', False))
    data['metadata']['feature_query_status'] = f"{with_features}/{len(data['black_holes'])} with features"
    data['metadata']['feature_query_date'] = "2026-05-23_retry"
    
    # Save
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Updated {json_path} ({with_features}/{len(data['black_holes'])} with features)")

def main():
    print("=" * 60)
    print("BlackCAT - Retry IR Color Query")
    print("=" * 60)
    
    # Step 1: Load failed sources
    failed_sources = load_failed_sources(
        json_path="data/known_bh_xray_binaries_features_v2.json"
    )
    
    if not failed_sources:
        print("[INFO] All sources already have features!")
        return
    
    # Step 2: Query IR colors for each failed source
    json_path = "data/known_bh_xray_binaries_features_v2.json"
    success_count = 0
    
    for bh in failed_sources:
        features = query_ir_colors(bh)
        
        if features:
            update_json_with_features(json_path, bh['name'], features)
            success_count += 1
        else:
            print(f"[ERROR] Failed to query IR colors for {bh['name']}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Failed sources: {len(failed_sources)}")
    print(f"Successfully queried: {success_count}")
    print(f"Still missing: {len(failed_sources) - success_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
