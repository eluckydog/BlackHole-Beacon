#!/usr/bin/env python3
"""Debug: Fetch and save raw Simbad HTML for inspection"""
import requests
import json

def load_top_candidate(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['top_20'][0]  # Get 1st candidate

def parse_anchor_name(name):
    """Parse J-name like J1840-0643 to RA/Dec in degrees"""
    ra_h = int(name[1:3])
    ra_m = int(name[3:5])
    dec_sign = -1 if name[5] == '-' else 1
    dec_d = int(name[6:8])
    dec_m = int(name[8:10])
    
    ra_deg = ra_h + ra_m / 60.0
    dec_deg = dec_sign * (dec_d + dec_m / 60.0)
    
    return ra_deg * 15.0, dec_deg  # RA in degrees

def fetch_simbad_html(ra_deg, dec_deg, radius=5):
    """Fetch Simbad HTML and save to file"""
    base_url = "http://simbad.u-strasbg.fr/simbad/sim-coo"
    params = {
        "Coord": f"+{ra_deg:.4f}{dec_deg:+.4f}",
        "Radius": radius,
        "Radius.unit": "arcmin",
        "submit": "submit+query"
    }
    
    print(f"[INFO] Fetching Simbad for RA={ra_deg:.4f}, Dec={dec_deg:+.4f}")
    print(f"[INFO] URL: {base_url}")
    print(f"[INFO] Params: {params}")
    
    resp = requests.get(base_url, params=params, timeout=30)
    resp.raise_for_status()
    
    print(f"[OK] HTTP {resp.status_code}, Length: {len(resp.text)} chars")
    
    # Save raw HTML
    output_path = "data/debug_simbad_html.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(resp.text)
    
    print(f"[OK] Saved raw HTML to: {output_path}")
    
    # Print first 2000 chars for inspection
    print("\n" + "="*60)
    print("FIRST 2000 CHARACTERS OF SIMBAD HTML:")
    print("="*60)
    print(resp.text[:2000])
    
    return resp.text

def main():
    print("="*60)
    print("Simbad HTML Debug Tool")
    print("="*60)
    
    # Load top candidate
    cand = load_top_candidate("data/v9_candidates_ir_cut_v1.json")
    name = cand['anchor']
    score = cand['score']
    
    print(f"\n[INFO] Top candidate: {name} (score={score:.3f})")
    
    # Parse coordinates
    ra_deg, dec_deg = parse_anchor_name(name)
    print(f"[INFO] Parsed coordinates: RA={ra_deg:.4f}°, Dec={dec_deg:+.4f}°")
    
    # Fetch HTML
    html = fetch_simbad_html(ra_deg, dec_deg, radius=5)
    
    print("\n" + "="*60)
    print("INSTRUCTIONS:")
    print("="*60)
    print("1. Check data/debug_simbad_html.txt")
    print("2. Look for 'Otype' or 'Psr' or 'BH*' in the HTML")
    print("3. Find the HTML structure (table? list? div?)")
    print("4. Tell me the structure, I'll fix the regex parser")

if __name__ == "__main__":
    main()
