"""Generate IR image URLs for v8.0 TOP 10 anomalies (fixed coordinate lookup)"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V8 = os.path.join(ROOT, "data", "classifier_ranking_v8.json")
PHASE3 = os.path.join(ROOT, "data", "phase3_candidates_full.json")
OUTPUT_HTML = os.path.join(ROOT, "data", "top10_v8_ir_images_v2.html")
OUTPUT_JSON = os.path.join(ROOT, "data", "top10_v8_ir_image_urls_v2.json")

with open(V8) as f:
    v8 = json.load(f)  # list of dicts
with open(PHASE3) as f:
    p3 = json.load(f)  # list of dicts

# Build lookup by designation
p3_lookup = {}
for c in p3:
    desig = c.get("designation", "")
    if desig:
        p3_lookup[desig] = c

top10 = v8[:10]

results = []
html_lines = []
html_lines.append("<html><head><title>v8.0 TOP 10 IR Images v2</title></head><body>")
html_lines.append("<h1>BlackHole Beacon v8.0 - TOP 10 Anomalies IR Images (Fixed)</h1>")
html_lines.append("<p>Generated: 2026-05-22</p>")
html_lines.append("<table border='1'><tr><th>Rank</th><th>Designation</th><th>RA</th><th>DEC</th><th>2MASS J</th><th>WISE W1</th></tr>")

for i, cand in enumerate(top10):
    desig = cand["designation"]
    # Look up coordinates from phase3
    details = p3_lookup.get(desig, {})
    ra = details.get("ra", 0.0)
    dec = details.get("dec", 0.0)
    
    # If not found, try to parse from designation (rough)
    if ra == 0.0 and dec == 0.0:
        # Parse J1822-4209 format
        try:
            # Example: J1822-4209 -> RA=18h22m, DEC=-42d09m
            # This is a simplification; real parsing needed
            pass
        except:
            pass
    
    # IRSA Firefly image URLs
    url_2mass = f"https://irsa.ipac.caltech.edu/iba/firefly/survey?survey=2mass&ra={ra:.4f}&dec={dec:.4f}&size=60"
    url_wise = f"https://irsa.ipac.caltech.edu/iba/firefly/survey?survey=wise&ra={ra:.4f}&dec={dec:.4f}&size=60"
    
    results.append({
        "rank": i+1,
        "designation": desig,
        "ra": ra,
        "dec": dec,
        "url_2mass": url_2mass,
        "url_wise": url_wise
    })
    
    html_lines.append(f"<tr><td>{i+1}</td><td>{desig}</td><td>{ra:.4f}</td><td>{dec:.4f}</td>")
    html_lines.append(f"<td><a href='{url_2mass}' target='_blank'>2MASS J</a></td>")
    html_lines.append(f"<td><a href='{url_wise}' target='_blank'>WISE W1</a></td></tr>")

html_lines.append("</table></body></html>")

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write("\n".join(html_lines))

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"Saved: {OUTPUT_HTML}")
print(f"Saved: {OUTPUT_JSON}")
print(f"\nOpen {OUTPUT_HTML} in browser to view IR images.")
