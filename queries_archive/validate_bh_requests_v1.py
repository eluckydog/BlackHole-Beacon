#!/usr/bin/env python3
"""
Validate BH candidates by querying Simbad via HTTP requests
(parse HTML to extract object types)
"""
import json
import requests
import re
import time

def load_candidates(json_path, top_n=10):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both list and dict formats
    if isinstance(data, list):
        return data[:top_n]
    elif isinstance(data, dict):
        # Try to get 'top_20' or 'candidates' key
        if 'top_20' in data:
            return data['top_20'][:top_n]
        elif 'candidates' in data:
            return data['candidates'][:top_n]
        else:
            # Return first list value found
            for v in data.values():
                if isinstance(v, list):
                    return v[:top_n]
            raise ValueError(f"Cannot find candidate list in {json_path}")
    else:
        raise TypeError(f"Unexpected JSON format: {type(data)}")

def parse_anchor_name(name):
    """Parse J-name like J1840-0643 to RA/Dec in degrees"""
    # J1840-0643 -> RA=18:40, Dec=-06:43
    ra_h = int(name[1:3])
    ra_m = int(name[3:5])
    dec_sign = -1 if name[5] == '-' else 1
    dec_d = int(name[6:8])
    dec_m = int(name[8:10])
    
    ra_deg = ra_h + ra_m / 60.0
    dec_deg = dec_sign * (dec_d + dec_m / 60.0)
    
    return ra_deg * 15.0, dec_deg  # RA in degrees

def query_simbad_html(ra_deg, dec_deg, radius=5):
    """Query Simbad via HTTP (direct URL construction)"""
    # Simbad sim-coo needs parameters in the URL path, not as GET params
    # URL format: http://simbad.u-strasbg.fr/simbad/sim-coo?Coord=+RA+Dec&Radius=5&Radius.unit=arcmin&submit=submit+query
    
    # Format coordinates: RA in degrees, Dec with sign
    ra_str = f"{ra_deg:.4f}"
    dec_str = f"{dec_deg:+.4f}"  # +N.NNNN or -N.NNNN
    
    # Construct full URL (encode spaces as +)
    url = f"http://simbad.u-strasbg.fr/simbad/sim-coo?Coord=+{ra_str}{dec_str}&Radius={radius}&Radius.unit=arcmin&submit=submit+query"
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"       [ERROR] Query failed: {e}")
        return None

def parse_simbad_html(html):
    """Parse Simbad HTML using regex (no BeautifulSoup needed)"""
    results = []
    
    # Pattern 1: Look for table rows with identifier and type
    # Simbad HTML structure: <tr>...<td>...</td><td>ID</td><td>TYPE</td>...
    
    # Find all table row blocks
    row_patterns = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
    
    for row_html in row_patterns:
        # Extract all <td> or <th> cells
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.DOTALL | re.IGNORECASE)
        
        if len(cells) >= 3:
            # Second cell = identifier, third cell = type
            obj_id = re.sub(r'<[^>]+>', '', cells[1]).strip()
            obj_type = re.sub(r'<[^>]+>', '', cells[2]).strip()
            
            if obj_id and obj_type and not obj_id.startswith('#'):
                results.append({
                    'id': obj_id,
                    'type': obj_type
                })
    
    # Pattern 2: Look for Otype= links (more reliable)
    # <a href="...Otype=Psr*">Psr*</a>
    otype_matches = re.findall(r'Otype=([A-Za-z*]+)', html)
    if otype_matches:
        # If we found Otype links, use them
        for ot in set(otype_matches):
            results.append({'id': 'unknown', 'type': ot})
    
    return results

def check_bh_indicators(obj_type):
    """Check if object type indicates BH/PSR/X-ray"""
    ot = obj_type.upper()
    
    # Check for exact type matches in the HTML
    if re.search(r'\bBH\*\b', ot):
        return 'BLACK_HOLE'
    if re.search(r'\bPSR\b', ot):
        return 'PULSAR'
    if re.search(r'\bX\b', ot) and not re.search(r'X-', ot):
        return 'XRAY'
    if re.search(r'LMXB', ot):
        return 'LMXB'
    if re.search(r'IMXB', ot):
        return 'IMXB'
    if re.search(r'CV\*', ot):
        return 'CV'
    if re.search(r'AGN', ot):
        return 'AGN'
    if re.search(r'\bG\b', ot):
        return 'GALAXY'
    
    return 'UNKNOWN'

def main():
    print("=" * 60)
    print("Black Hole Candidate Validation (requests + BeautifulSoup)")
    print("=" * 60)
    
    candidates = load_candidates("data/v9_candidates_ir_cut_v1.json", top_n=10)
    print(f"[INFO] Loaded {len(candidates)} candidates\n")
    
    results = []
    
    for i, cand in enumerate(candidates, 1):
        name = cand.get('anchor', cand.get('name', f'cand_{i}'))
        score = cand.get('score', cand.get('anomaly_score', 0))
        
        print(f"\n[{i}/{len(candidates)}] {name} (score={score:.3f})")
        
        # Parse coordinates from name
        try:
            ra_deg, dec_deg = parse_anchor_name(name)
            print(f"       RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°")
        except:
            print(f"       [WARN] Cannot parse coordinates from {name}")
            results.append({
                'rank': i,
                'name': name,
                'score': score,
                'simbad_status': 'PARSE_ERROR'
            })
            continue
        
        # Query Simbad
        html = query_simbad_html(ra_deg, dec_deg, radius=5)
        
        if html is None:
            print(f"       [ERROR] Simbad query failed")
            results.append({
                'rank': i,
                'name': name,
                'score': score,
                'simbad_status': 'QUERY_FAILED'
            })
            time.sleep(1)
            continue
        
        # Parse results
        simbad_results = parse_simbad_html(html)
        
        if not simbad_results:
            print(f"       [INFO] No Simbad results (might be new!)")
            results.append({
                'rank': i,
                'name': name,
                'score': score,
                'simbad_status': 'NOT_FOUND',
                'is_known': False,
                'object_type': None
            })
        else:
            # Check for BH/PSR indicators
            found_indicators = []
            for res in simbad_results[:5]:  # Check top 5 matches
                indicator = check_bh_indicators(res['type'])
                if indicator != 'UNKNOWN':
                    found_indicators.append(indicator)
            
            if found_indicators:
                print(f"       [FOUND] Known source! Types: {', '.join(set(found_indicators))}")
                results.append({
                    'rank': i,
                    'name': name,
                    'score': score,
                    'simbad_status': 'KNOWN',
                    'is_known': True,
                    'object_types': found_indicators
                })
            else:
                print(f"       [INFO] Found {len(simbad_results)} sources, but no BH/PSR indicators")
                results.append({
                    'rank': i,
                    'name': name,
                    'score': score,
                    'simbad_status': 'FOUND_NO_INDICATOR',
                    'is_known': True,
                    'object_types': [r['type'] for r in simbad_results[:3]]
                })
        
        time.sleep(1)  # Be nice to Simbad
    
    # Save results
    output_path = "data/validation_bh_requests_v1.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"SUMMARY")
    print("=" * 60)
    print(f"Validated: {len(results)}")
    print(f"Known sources: {sum(1 for r in results if r.get('is_known'))}")
    print(f"Possible new: {sum(1 for r in results if not r.get('is_known'))}")
    print(f"\nOutput: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
