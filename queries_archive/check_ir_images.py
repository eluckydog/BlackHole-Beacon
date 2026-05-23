"""
Generate IR image URLs for TOP 10 anomalies (v8.0).

WHY? To visually inspect if they are point sources (pulsar/BH) or galaxies (AGN).
Point source -> likely pulsar/BH.
Galaxy -> likely AGN (false positive).

Steps:
1. Generate 2MASS (J, H, K bands) image URLs
2. Generate WISE (W1, W2, W3 bands) image URLs
3. Save URLs to JSON for easy browsing
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

print("BlackHole Beacon — Generate IR Image URLs for TOP 10 (v8.0)")
print("="*80)

# ==========
# 1. Load v8.0 TOP 10
# ==========
print("\n--- 1. Load v8.0 TOP 10 ---")

ranking_file = os.path.join(DATA_DIR, "classifier_ranking_v8.json")
with open(ranking_file, "r") as f:
    ranking = json.load(f)

top10 = ranking[:10]

print(f"  TOP 10 anomalies (v8.0):")
for i, r in enumerate(top10):
    print(f"    {i+1}. {r['anchor']} (prob={r['prob']:.4f})")

# ==========
# 2. Load candidate details (RA/DEC)
# ==========
print("\n--- 2. Load Candidate Details (RA/DEC) ---")

phase3_file = os.path.join(DATA_DIR, "phase3_candidates_full.json")
with open(phase3_file, "r") as f:
    candidates = json.load(f)

# Build anchor -> candidate mapping
candidate_dict = {c.get("anchor", f"UNK_{i}"): c for i, c in enumerate(candidates)}

# Get RA/DEC for TOP 10
top10_details = []
for r in top10:
    anchor = r["anchor"]
    if anchor in candidate_dict:
        c = candidate_dict[anchor]
        ra = c.get("ra", 0.0) or 0.0
        dec = c.get("dec", 0.0) or 0.0
        top10_details.append({
            "anchor": anchor,
            "ra": ra,
            "dec": dec,
            "prob": r["prob"]
        })
    else:
        print(f"  WARNING: {anchor} not found in phase3_candidates_full.json")

print(f"  Loaded RA/DEC for {len(top10_details)} / 10 anomalies")

# ==========
# 3. Generate IR image URLs
# ==========
print("\n--- 3. Generate IR Image URLs ---")

# Base URLs for IR surveys
# 2MASS: https://irsa.ipac.caltech.edu/galex.html
# WISE: https://irsa.ipac.caltech.edu/wise.html
# DSS: https://archive.stsci.edu/cgi-bin/dss_form

ir_urls = []

for det in top10_details:
    anchor = det["anchor"]
    ra = det["ra"]
    dec = det["dec"]
    
    # Format RA/DEC for URL (decimal degrees)
    # Some archives want HHhMMmSS.Ss / DDdMMmSS.Ss format
    # We'll use decimal degrees (simpler)
    
    # 2MASS image URL (J, H, K bands)
    # IRSA Viewer: https://irsa.ipac.caltech.edu/galex.html
    twomass_url = f"https://irsa.ipac.caltech.edu/cgi-bin/2MASS/IM/judith.pl?RA={ra}&DEC={dec}&SIZE=300"
    
    # WISE image URL (W1, W2, W3 bands)
    # IRSA Viewer: https://irsa.ipac.caltech.edu/wise.html
    wise_url = f"https://irsa.ipac.caltech.edu/cgi-bin/WiseView/judith.pl?RA={ra}&DEC={dec}&SIZE=300"
    
    # DSS (optical) image URL (for comparison)
    # STScI DSS: https://archive.stsci.edu/cgi-bin/dss_form
    dss_url = f"https://archive.stsci.edu/cgi-bin/dss_form?RA={ra}&DEC={dec}&SIZE=5&FORMAT=GIF"
    
    # Simbad info page
    simbad_url = f"https://simbad.u-strasbg.fr/simbad/sim-coo?Coord={ra}+{dec}&Radius=10&Radius.unit=arcmin"
    
    ir_urls.append({
        "anchor": anchor,
        "ra": ra,
        "dec": dec,
        "prob": det["prob"],
        "urls": {
            "2MASS": twomass_url,
            "WISE": wise_url,
            "DSS (optical)": dss_url,
            "Simbad": simbad_url
        }
    })
    
    print(f"\n  {anchor} (RA={ra:.4f}, DEC={dec:.4f}, prob={det['prob']:.4f})")
    print(f"    2MASS: {twomass_url}")
    print(f"    WISE:   {wise_url}")
    print(f"    DSS:    {dss_url}")
    print(f"    Simbad: {simbad_url}")

# ==========
# 4. Save URLs to JSON
# ==========
print("\n--- 4. Save URLs to JSON ---")

urls_file = os.path.join(DATA_DIR, "top10_ir_image_urls.json")
with open(urls_file, "w") as f:
    json.dump(ir_urls, f, indent=2)

print(f"  Saved: {urls_file}")
print(f"  Contains {len(ir_urls)} entries (TOP 10 anomalies)")

# ==========
# 5. Generate HTML report (for easy viewing)
# ==========
print("\n--- 5. Generate HTML Report ---")

html_file = os.path.join(DATA_DIR, "top10_ir_images.html")

html_content = """<!DOCTYPE html>
<html>
<head>
    <title>BlackHole Beacon — TOP 10 Anomalies (v8.0) IR Images</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
        }}
        .candidate {{
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .anchor {{
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .prob {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .coords {{
            color: #7f8c8d;
            font-family: monospace;
        }}
        .image-links {{
            margin-top: 10px;
        }}
        .image-links a {{
            display: inline-block;
            margin-right: 15px;
            padding: 5px 10px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 3px;
        }}
        .image-links a:hover {{
            background-color: #2980b9;
        }}
        iframe {{
            width: 100%;
            height: 300px;
            border: 1px solid #ddd;
            border-radius: 3px;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <h1>BlackHole Beacon — TOP 10 Anomalies (v8.0) IR Images</h1>
    <p>Visual inspection: point source → likely pulsar/BH; galaxy → likely AGN (false positive).</p>
"""

for item in ir_urls:
    anchor = item["anchor"]
    ra = item["ra"]
    dec = item["dec"]
    prob = item["prob"]
    urls = item["urls"]
    
    html_content += f"""
    <div class="candidate">
        <div class="anchor">{anchor}</div>
        <div class="prob">Anomaly Probability: {prob:.4f}</div>
        <div class="coords">RA={ra:.4f}, DEC={dec:.4f}</div>
        <div class="image-links">
            <a href="{urls['2MASS']}" target="_blank">2MASS (IR)</a>
            <a href="{urls['WISE']}" target="_blank">WISE (IR)</a>
            <a href="{urls['DSS (optical)']}" target="_blank">DSS (Optical)</a>
            <a href="{urls['Simbad']}" target="_blank">Simbad</a>
        </div>
        <iframe src="{urls['WISE']}"></iframe>
    </div>
    """

html_content += """
</body>
</html>
"""

with open(html_file, "w") as f:
    f.write(html_content)

print(f"  Saved: {html_file}")
print(f"  Open this file in a browser to view IR images.")

# ==========
# 6. Summary
# ==========
print("\n" + "="*80)
print("SUMMARY:")
print("="*80)

print(f"""
  TOP 10 anomalies (v8.0) IR image URLs generated.
  
  Files generated:
    1. {urls_file}
    2. {html_file}
  
  NEXT STEPS:
    1. Open {html_file} in a browser
    2. Visually inspect each candidate:
       - Point source (no extended structure) -> likely pulsar/BH
       - Extended source (galaxy morphology) -> likely AGN (false positive)
    3. For point sources:
       - Check X-ray/radio (from cross-match results)
       - If X-ray/radio detected -> high priority candidate
    4. For galaxies:
       - Likely AGN (false positive) -> remove from candidate list
""")

print("="*80)
print("DONE. IR image URLs generated.")
print("="*80)
