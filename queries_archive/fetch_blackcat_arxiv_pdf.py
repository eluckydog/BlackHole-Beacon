#!/usr/bin/env python3
"""
Fetch BlackCAT catalog from arXiv PDF (1510.06734) and extract tables.
Use pdfplumber to extract tables from PDF.
"""

import os
import json
import requests
import pdfplumber
from io import BytesIO

def fetch_arxiv_pdf(arxiv_id="1510.06734", output_path="data/blackcat_paper.pdf"):
    """Download arXiv PDF."""
    # arXiv PDF URL
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    
    print(f"[INFO] Downloading arXiv PDF: {url}")
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        # Save PDF
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"[OK] Saved PDF to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"[ERROR] Failed to download PDF: {e}")
        return None

def extract_tables_from_pdf(pdf_path):
    """Extract tables from PDF using pdfplumber."""
    print(f"[INFO] Extracting tables from: {pdf_path}")
    
    tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                print(f"[INFO] Processing page {page_num}/{len(pdf.pages)}")
                
                # Extract tables from this page
                page_tables = page.extract_tables()
                
                if page_tables:
                    print(f"[INFO] Found {len(page_tables)} table(s) on page {page_num}")
                    
                    for table_idx, table in enumerate(page_tables):
                        if table and len(table) > 1:  # Has header + data
                            tables.append({
                                "page": page_num,
                                "table_idx": table_idx,
                                "header": table[0],
                                "rows": table[1:],
                                "num_rows": len(table) - 1
                            })
                            print(f"[INFO]   Table {table_idx+1}: {len(table)-1} rows, header: {table[0][:3]}...")
                
        print(f"[OK] Total tables extracted: {len(tables)}")
        return tables
        
    except Exception as e:
        print(f"[ERROR] Failed to extract tables: {e}")
        return []

def parse_blackcat_tables(tables):
    """Parse extracted tables, looking for BlackCAT catalog (Table 5)."""
    print(f"[INFO] Parsing {len(tables)} tables for BlackCAT catalog...")
    
    blackcat_entries = []
    
    for table in tables:
        header = table["header"]
        rows = table["rows"]
        
        # Check if this looks like BlackCAT catalog
        # Typical columns: Name, RA, Dec, l, b, Porb, ...
        header_str = " ".join([str(h).lower() for h in header if h])
        
        if "name" in header_str and ("ra" in header_str or "deg" in header_str):
            print(f"[INFO] Found potential BlackCAT table on page {table['page']}")
            print(f"[INFO]   Header: {header}")
            
            # Parse rows
            for row_idx, row in enumerate(rows, start=2):
                try:
                    # BlackCAT columns (from paper):
                    # Column 1: Name (e.g., XTE J1118+480)
                    # Column 2: RA (deg)
                    # Column 3: Dec (deg)
                    # Column 4: l (deg)
                    # Column 5: b (deg)
                    # Column 6: Porb (hr)
                    # ...
                    
                    if len(row) >= 6 and row[0] and row[1] and row[2]:
                        entry = {
                            "name": str(row[0]).strip(),
                            "ra_deg": parse_ra_dec(str(row[1]).strip()),
                            "dec_deg": parse_ra_dec(str(row[2]).strip()),
                            "raw_row": [str(c).strip() if c else "" for c in row]
                        }
                        
                        # Only add if name looks like X-ray binary
                        if entry["name"].startswith(("XTE", "GRO", "Swift", "MAXI", "1A", "4U", "V")):
                            blackcat_entries.append(entry)
                            if len(blackcat_entries) <= 5:
                                print(f"[INFO]   Parsed: {entry['name']} at RA={entry['ra_deg']}, Dec={entry['dec_deg']}")
                
                except Exception as e:
                    print(f"[WARN] Failed to parse row {row_idx}: {e}")
                    continue
        
        if len(blackcat_entries) >= 20:
            print(f"[INFO] Found {len(blackcat_entries)} entries, stopping search")
            break
    
    print(f"[OK] Total BlackCAT entries parsed: {len(blackcat_entries)}")
    return blackcat_entries

def parse_ra_dec(value_str):
    """Parse RA or Dec value from string."""
    try:
        # Try direct float conversion
        return float(value_str)
    except:
        try:
            # Try HH:MM:SS.s format
            parts = value_str.split(":")
            if len(parts) == 3:
                h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
                return (h + m/60.0 + s/3600.0) * 15.0  # Convert HA to deg
        except:
            pass
    
    return None

def save_to_json(entries, output_path="data/blackcat_from_arxiv.json"):
    """Save parsed entries to JSON."""
    print(f"[INFO] Saving {len(entries)} entries to: {output_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    result = {
        "metadata": {
            "source": "arXiv:1510.06734 PDF extraction",
            "extraction_date": "2026-05-23",
            "note": "BlackCAT catalog (Table 5) extracted from PDF using pdfplumber"
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
    print("BlackCAT Catalog - arXiv PDF Extraction")
    print("=" * 60)
    
    # Step 1: Download arXiv PDF
    pdf_path = fetch_arxiv_pdf(
        arxiv_id="1510.06734",
        output_path="data/blackcat_paper.pdf"
    )
    
    if not pdf_path:
        print("[ERROR] Failed to download PDF. Try manual download.")
        return
    
    # Step 2: Extract tables from PDF
    tables = extract_tables_from_pdf(pdf_path)
    
    if not tables:
        print("[ERROR] No tables found in PDF. Try manual parsing.")
        return
    
    # Step 3: Parse BlackCAT tables
    entries = parse_blackcat_tables(tables)
    
    if not entries:
        print("[ERROR] No BlackCAT entries found. Check PDF table format.")
        return
    
    # Step 4: Save to JSON
    output_path = save_to_json(
        entries,
        output_path="data/blackcat_from_arxiv.json"
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Tables extracted: {len(tables)}")
    print(f"BlackCAT entries parsed: {len(entries)}")
    print(f"Output: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
