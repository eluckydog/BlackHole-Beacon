#!/usr/bin/env python3
"""
Fetch BlackCAT catalog from CDS (machine-readable format).
Download .dat file and parse ASCII table.
"""

import os
import json
import urllib.request
import csv
from io import StringIO

def fetch_cds_dat(cat_id="J/ApJ/813/L5", table="table5", output_path="data/blackcat_cds.dat"):
    """Download .dat file from CDS."""
    # CDS URL for machine-readable table
    url = f"http://cdsarc.u-strasbg.fr/viz-bin/nph-Cat?{cat_id}/{table}"
    
    print(f"[INFO] Downloading CDS table: {url}")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read().decode('utf-8', errors='ignore')
        
        # Save raw data
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(data)
        
        print(f"[OK] Saved raw data to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"[ERROR] Failed to download from CDS: {e}")
        return None

def parse_cds_dat(dat_path):
    """Parse CDS .dat file (ASCII table with fixed-width or delimiter-separated)."""
    print(f"[INFO] Parsing CDS .dat file: {dat_path}")
    
    entries = []
    
    try:
        with open(dat_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Find data rows (skip header lines starting with # or space)
        data_lines = []
        header_line = None
        
        for line in lines:
            line = line.rstrip('\n\r')
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Skip comment lines (starting with #)
            if line.startswith('#'):
                # Check if this is a header line
                if 'Name' in line or 'RA' in line or 'Dec' in line:
                    header_line = line
                continue
            
            # Data line (doesn't start with # or space)
            if not line[0].isspace() and not line.startswith('|'):
                data_lines.append(line)
        
        print(f"[INFO] Found {len(data_lines)} data lines")
        
        # Try to parse as fixed-width or delimiter-separated
        for line_num, line in enumerate(data_lines, start=1):
            try:
                # Try tab-separated first
                if '\t' in line:
                    parts = line.split('\t')
                # Try pipe-separated
                elif '|' in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                # Try space-separated (fixed-width)
                else:
                    # Assume fixed-width columns (CDS format)
                    # Typical BlackCAT columns: Name, RA, Dec, l, b, Porb, ...
                    parts = line.split()
                
                if len(parts) >= 3:
                    # Try to extract name, RA, Dec
                    name = parts[0].strip()
                    
                    # Validate name (should look like X-ray binary name)
                    if name and (name[0].isupper() or name.startswith('XTE') or name.startswith('GRO')):
                        entry = {
                            "name": name,
                            "raw_line": line,
                            "parts": parts[:10]  # First 10 columns
                        }
                        
                        # Try to parse RA/Dec if numeric
                        try:
                            if len(parts) >= 3:
                                ra_str = parts[1].strip()
                                dec_str = parts[2].strip()
                                
                                # Try to parse as float (degrees)
                                ra_deg = float(ra_str) if ra_str.replace('.', '').isdigit() else None
                                dec_deg = float(dec_str) if dec_str.replace('.', '').isdigit() else None
                                
                                entry["ra_deg"] = ra_deg
                                entry["dec_deg"] = dec_deg
                        except:
                            pass
                        
                        entries.append(entry)
                        
                        if len(entries) <= 5:
                            print(f"[INFO]   Parsed: {name} (RA={entry.get('ra_deg')}, Dec={entry.get('dec_deg')})")
                
            except Exception as e:
                print(f"[WARN] Failed to parse line {line_num}: {e}")
                continue
        
        print(f"[OK] Total entries parsed: {len(entries)}")
        return entries
        
    except Exception as e:
        print(f"[ERROR] Failed to parse .dat file: {e}")
        return []

def save_to_json(entries, output_path="data/blackcat_from_cds.json"):
    """Save parsed entries to JSON."""
    print(f"[INFO] Saving {len(entries)} entries to: {output_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    result = {
        "metadata": {
            "source": "CDS VizieR (J/ApJ/813/L5)",
            "download_date": "2026-05-23",
            "note": "BlackCAT catalog downloaded from CDS in machine-readable format"
        },
        "num_entries": len(entries),
        "entries": entries
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved to: {output_path}")
    return output_path

def main():
    print("=" * 60)
    print("BlackCAT Catalog - CDS Download")
    print("=" * 60)
    
    # Step 1: Download from CDS
    dat_path = fetch_cds_dat(
        cat_id="J/ApJ/813/L5",
        table="table5",
        output_path="data/blackcat_cds.dat"
    )
    
    if not dat_path:
        print("[ERROR] Failed to download from CDS. Try VizieR direct query.")
        return
    
    # Step 2: Parse .dat file
    entries = parse_cds_dat(dat_path)
    
    if not entries:
        print("[ERROR] No entries found. Check .dat file format.")
        return
    
    # Step 3: Save to JSON
    output_path = save_to_json(
        entries,
        output_path="data/blackcat_from_cds.json"
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Entries parsed: {len(entries)}")
    print(f"Output: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
