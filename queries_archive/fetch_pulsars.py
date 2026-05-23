"""Fetch Pulsar catalog from VizieR B/psr - try multiple formats"""
import urllib.request, ssl, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

OUT = os.path.join(os.path.dirname(__file__).replace("queries", "catalog"))
os.makedirs(OUT, exist_ok=True)

# Try these formats
queries = [
    ("B/psr/psr CSV", "https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=B/psr/psr&-out.max=99999&-out.form=CSV&-out.add=_r"),
    ("B/psr TSV", "https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=B/psr/psr&-out.max=99999&-out.form=TSV"),
    ("B/psr txt", "https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=B/psr/psr&-out.max=99999&-out.form=txt"),
    ("B/psr TDF", "https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=B/psr/psr&-out.max=99999&-out.form=TABLEDEF"),
    ("B/psr VOTable", "https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=B/psr/psr&-out.max=99999&-out.form=VOTable"),
]

for label, url in queries:
    print(f"\n=== {label} ===")
    try:
        req = urllib.request.Request(url)
        req.add_header('Accept', 'text/plain, text/csv, text/tab-separated-values')
        req.add_header('User-Agent', 'Mozilla/5.0')
        resp = urllib.request.urlopen(req, timeout=20, context=ctx)
        raw = resp.read()
        text = raw.decode('utf-8', errors='replace')
        ct = resp.getheader('Content-Type', '')
        
        print(f"  Status: {resp.status}, CT: {ct}, Size: {len(raw):,} bytes")
        
        if len(raw) < 200:
            print(f"  Too small: {text[:200]}")
            continue
            
        # Check if it looks like data (not HTML menu)
        data_lines = [l for l in text.split('\n') if l.strip() and not l.strip().startswith('<')]
        html_lines = [l for l in text.split('\n') if '<html' in l.lower() or '<head' in l.lower()]
        
        if html_lines:
            # It's HTML - check if data is embedded
            j_count = text.count('J00') + text.count('J0') 
            print(f"  HTML with ~{j_count} J-name references (show form page)")
            
            # Try with POST approach instead
            if "show form page" in text[:500] or j_count == 0:
                continue
        
        # Check if it's real data
        if '#' in text[:50] or '---' in text[:100] or text.split('\n')[0].strip().startswith('J00'):
            print(f"  First line: {text.split(chr(10))[0][:150]}")
            print(f"  Looks like actual data!")
            outpath = os.path.join(OUT, "psrcat_vizier_data" + (".csv" if "CSV" in label else ".txt"))
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  Saved: {outpath}")
            break
        
        # Generic check
        lines = text.split('\n')
        print(f"  Lines: {len(lines)}, First: {lines[0][:100]}")
        
    except Exception as e:
        print(f"  ERROR: {e}")

# Last resort: parse the HTML we already have
print("\n=== Parsing existing HTML for pulsar data ===")
html_path = os.path.join(OUT, "psrcat_vizier.csv")
if os.path.exists(html_path):
    import re
    text = open(html_path, encoding='utf-8', errors='replace').read()
    
    # Pattern: <INPUT ... recno=N;-go;">  JNAME  ... data fields
    # Extract lines with pulsar names and positions
    pattern = re.compile(
        r'recno=(\d+);.*?>\s+(J\d{4}[+-]\d{2,4}\S*)\s+'
        r'.*?>\s+(\d{2})\s+(\d{2})\s+(\d{2}\.\d*)\s+'  # RA
        r'([-+]?\d{2})\s+(\d{2})\s+(\d{2}\.\d*)'       # Dec
    )
    
    matches = pattern.findall(text)
    print(f"  Parsed {len(matches)} pulsar entries")
    
    if matches:
        csv_out = os.path.join(OUT, "psrcat_parsed.csv")
        with open(csv_out, "w", encoding="utf-8") as f:
            f.write("recno,JName,RAh,RAm,RAs,DecSign,Decd,Decm,Decs\n")
            for m in matches:
                f.write(f"{m[0]},{m[1]},{m[2]},{m[3]},{m[4]},{m[5]},{m[6]},{m[7]}\n")
        print(f"  Saved: psrcat_parsed.csv ({len(matches)} entries)")
        
        # Show sample
        for m in matches[:5]:
            print(f"    {m[1]}: RA={m[2]}:{m[3]}:{m[4]} Dec={m[5]}:{m[6]}:{m[7]}")