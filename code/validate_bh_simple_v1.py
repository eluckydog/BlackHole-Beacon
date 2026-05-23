#!/usr/bin/env python3
"""Simple Simbad validation - search HTML for keywords directly"""
import json
import requests
import time
import re

def load_top_candidates(json_path, top_n=10):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'top_20' in data:
        return data['top_20'][:top_n]
    return []

def parse_anchor_to_radec(name):
    """Parse J-name like J1840-0643 to RA/Dec in degrees"""
    ra_h = int(name[1:3])
    ra_m = int(name[3:5])
    dec_sign = -1 if name[5] == '-' else 1
    dec_d = int(name[6:8])
    dec_m = int(name[8:10])
    
    ra_deg = ra_h + ra_m / 60.0
    dec_deg = dec_sign * (dec_d + dec_m / 60.0)
    
    return ra_deg * 15.0, dec_deg  # RA in degrees

def query_simbad_html(ra_deg, dec_deg, radius=5):
    """Query Simbad via direct URL construction"""
    ra_str = f"{ra_deg:.4f}"
    dec_str = f"{dec_deg:+.4f}"
    
    url = f"http://simbad.u-strasbg.fr/simbad/sim-coo?Coord=+{ra_str}{dec_str}&Radius={radius}&Radius.unit=arcmin&submit=submit+query"
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"       [ERROR] Query failed: {e}")
        return None

def check_html_for_indicators(html):
    """Search HTML directly for BH/PSR/X-ray indicators"""
    if not html:
        return 'UNKNOWN', []
    
    indicators_found = []
    
    # Search for common object types in HTML
    # Pattern: Otype=XXX in links, or text like "Psr", "BH*", etc.
    patterns = [
        (r'Otype=(Psr\*)', 'PULSAR'),
        (r'\b(Psr\w*)\b', 'PULSAR'),
        (r'Otype=(BH\*)', 'BLACK_HOLE'),
        (r'\b(BH\*)\b', 'BLACK_HOLE'),
        (r'Otype=(X\b)', 'XRAY'),
        (r'\b(LMXB)\b', 'LMXB'),
        (r'\b(IMXB)\b', 'IMXB'),
        (r'\b(CV\*)\b', 'CV'),
        (r'\b(AGN)\b', 'AGN'),
    ]
    
    for pattern, label in patterns:
        if re.search(pattern, html, re.IGNORECASE):
            indicators_found.append(label)
    
    if indicators_found:
        return indicators_found[0], indicators_found
    return 'UNKNOWN', []

def main():
    print("="*60)
    print("Black Hole Candidate Validation (Simple Keyword Search)")
    print("="*60)
    
    candidates = load_top_candidates("data/v9_candidates_ir_cut_v1.json", top_n=10)
    print(f"[INFO] Loaded {len(candidates)} candidates\n")
    
    results = []
    
    for i, cand in enumerate(candidates, 1):
        name = cand['anchor']
        score = cand['score']
        
        print(f"[{i}/{len(candidates)}] {name} (score={score:.3f})")
        
        # Parse coordinates
        ra_deg, dec_deg = parse_anchor_to_radec(name)
        print(f"       RA={ra_deg:.4f}°, Dec={dec_deg:+.4f}°")
        
        # Query Simbad
        html = query_simbad_html(ra_deg, dec_deg, radius=5)
        
        if html is None:
            print(f"       [ERROR] Query failed\n")
            results.append({
                'rank': i,
                'anchor': name,
                'score': score,
                'simbad_status': 'error',
                'indicator': 'UNKNOWN'
            })
            time.sleep(1)
            continue
        
        # Check for indicators
        indicator, all_indicators = check_html_for_indicators(html)
        
        # Count sources (rough: count <tr> tags)
        num_sources = html.count('<tr')
        
        print(f"       [INFO] Found ~{num_sources} HTML rows, indicator={indicator}")
        
        results.append({
            'rank': i,
            'anchor': name,
            'score': score,
            'simbad_status': 'ok',
            'num_sources_est': num_sources,
            'indicator': indicator,
            'all_indicators': all_indicators
        })
        
        time.sleep(1)  # Be polite
    
    # Save results
    output_path = "data/validation_bh_simple_v1.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Validated: {len(results)}")
    
    known = sum(1 for r in results if r['indicator'] != 'UNKNOWN')
    unknown = sum(1 for r in results if r['indicator'] == 'UNKNOWN')
    
    print(f"Known sources (with indicators): {known}")
    print(f"Possible new (no indicators): {unknown}")
    print(f"\nOutput: {output_path}")
    print("="*60)

if __name__ == "__main__":
    main()
