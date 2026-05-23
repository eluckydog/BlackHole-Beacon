"""BlackHole Beacon — Simbad Cross-Comparison v1.2

Queries Simbad at anchor positions for object classification.
Uses BINARY VOTable parser for Simbad TAP responses.
"""

import json, os, sys, time, csv
import urllib.request, urllib.parse, ssl
import struct, base64
import xml.etree.ElementTree as ET
from datetime import datetime

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
TAP = "https://simbad.u-strasbg.fr/simbad/sim-tap/sync"
H = {"User-Agent": "BHBeacon/1.0"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR_DIR = os.path.join(ROOT, "catalog")
FEATURES_FILE = os.path.join(ROOT, "data", "spectral_features.json")
OUTPUT = os.path.join(ROOT, "data", "simbad_comparison.json")
REPORT = os.path.join(ROOT, "data", "simbad_comparison_report.md")

def simbad_query(ra, dec, rad=5.0/3600.0):
    sql = ("SELECT main_id, ra, dec, otype, otype_txt, "
           "pmra, pmdec, plx_value, plx_err, sp_type "
           "FROM basic "
           "WHERE CONTAINS(POINT('ICRS', ra, dec), "
           "CIRCLE('ICRS', " + str(ra) + ", " + str(dec) + ", " + str(rad) + "))=1")
    params = {"request":"doQuery","lang":"ADQL","format":"VOTABLE","query":sql}
    url = TAP + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=H)
    resp = urllib.request.urlopen(req, timeout=25, context=ctx)
    return parse_votable(resp.read().decode("utf-8"))

def parse_votable(text):
    try:
        root = ET.fromstring(text)
    except:
        return []
    for info in root.iter():
        t = info.tag.split("}")[-1]
        if t == "INFO" and "ERROR" in info.get("value","").upper():
            return []
    for rsrc in root.iter():
        rt = rsrc.tag.split("}")[-1]
        if rt != "RESOURCE" or rsrc.get("type") != "results":
            continue
        table = None
        for c in rsrc:
            ct = c.tag.split("}")[-1]
            if ct == "TABLE":
                table = c; break
        if table is None:
            continue
        fields = []
        for c in table:
            ct = c.tag.split("}")[-1]
            if ct == "FIELD":
                fields.append({"name":c.get("name",""),"datatype":c.get("datatype","char"),"arraysize":c.get("arraysize","*")})
        data_el = None
        for c in table:
            if c.tag.split("}")[-1] == "DATA":
                data_el = c; break
        if data_el is None:
            continue
        # TABLEDATA
        td = None
        for c in data_el:
            if c.tag.split("}")[-1] == "TABLEDATA":
                td = c; break
        if td is not None:
            rows = []
            for tr in td:
                if tr.tag.split("}")[-1] != "TR":
                    continue
                vals = [td.text or "" for td in tr if td.tag.split("}")[-1] == "TD"]
                if vals:
                    rows.append(dict(zip([f["name"] for f in fields], vals)))
            return rows
        # BINARY
        bin_el = None
        for c in data_el:
            if c.tag.split("}")[-1] == "BINARY":
                bin_el = c; break
        if bin_el is not None:
            stream_el = None
            for c in bin_el:
                if c.tag.split("}")[-1] == "STREAM":
                    stream_el = c; break
            if stream_el is not None and stream_el.text:
                raw = base64.b64decode(stream_el.text.strip())
                return parse_binary(raw, fields)
    return []

def parse_binary(raw, fields):
    rows = []
    offset = 0
    while offset < len(raw) and len(rows) < 1000:
        row = {}
        for f in fields:
            if offset >= len(raw):
                break
            name = f["name"]
            dtype = f["datatype"]
            if dtype == "char":
                if offset + 4 > len(raw):
                    break
                strlen = struct.unpack(">I", raw[offset:offset+4])[0]
                offset += 4
                if strlen > 0 and offset + strlen <= len(raw):
                    row[name] = raw[offset:offset+strlen].decode("utf-8", errors="replace")
                    offset += strlen
                else:
                    row[name] = ""
                    if strlen > 0:
                        offset = min(offset, len(raw))
            elif dtype == "double":
                if offset + 8 <= len(raw):
                    row[name] = struct.unpack(">d", raw[offset:offset+8])[0]
                    offset += 8
                else:
                    break
            elif dtype == "float":
                if offset + 4 <= len(raw):
                    row[name] = struct.unpack(">f", raw[offset:offset+4])[0]
                    offset += 4
                else:
                    break
            else:
                offset += 8
        if row:
            rows.append(row)
    return rows

def load_anchors(limit=100):
    anchors = []
    for fname, atype in [("bh_xrb_catalog.csv", "bh_xrb"),
                          ("smbh_catalog.csv", "smbh"),
                          ("psrcat_catalog.csv", "pulsar")]:
        fp = os.path.join(ANCHOR_DIR, fname)
        if not os.path.exists(fp):
            continue
        with open(fp, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    ra = float(row.get("RA_deg", 0))
                    dec = float(row.get("Dec_deg", 0))
                    if ra == 0 and dec == 0:
                        continue
                    anchors.append({
                        "name": (row.get("JName") or row.get("Name") or "").strip(),
                        "ra": ra, "dec": dec, "type": atype,
                    })
                    if len(anchors) >= limit:
                        return anchors
                except:
                    continue
    return anchors

# Load SED features
with open(FEATURES_FILE) as f:
    sed_db = json.load(f)
sed_lookup = {s["anchor"]: s for s in sed_db}

anchors = load_anchors(limit=50)
print("BlackHole Beacon - Simbad Cross-Comparison v1.2")
print("=" * 55)
print("Anchors: " + str(len(anchors)))

results = []
pulsar_classified = 0
matched = 0
type_counts = {}
discrepancies = []

last_q = 0
for i, a in enumerate(anchors):
    now = time.time()
    if now - last_q < 0.3:
        time.sleep(0.3 - (now - last_q))
    last_q = time.time()

    sys.stdout.write("\r  [" + str(i+1) + "/" + str(len(anchors)) + "] " + a["name"][:20].ljust(20) + " ")
    sys.stdout.flush()

    rows = simbad_query(a["ra"], a["dec"])

    if not rows:
        results.append({"anchor": a["name"], "type": a["type"], "error": "no simbad match"})
        continue

    matched += 1
    b = rows[0]
    otype = str(b.get("otype", ""))
    otype_txt = str(b.get("otype_txt", ""))

    type_counts[otype] = type_counts.get(otype, 0) + 1

    if otype == "Psr":
        pulsar_classified += 1

    if otype != "Psr" and a["type"] == "pulsar":
        discrepancies.append({"anchor": a["name"], "expected": "pulsar", "simbad": otype_txt, "simbad_otype": otype})

    plx = b.get("plx_value")
    sp = b.get("sp_type", "")
    pmra = b.get("pmra")
    pmdec = b.get("pmdec")

    entry = {
        "anchor": a["name"],
        "type": a["type"],
        "simbad": {
            "main_id": b.get("main_id", ""),
            "otype": otype,
            "otype_txt": otype_txt,
            "pmra_masyr": round(pmra, 1) if isinstance(pmra, float) else ("?") if isinstance(pmra, str) else str(pmra),
            "pmdec_masyr": round(pmdec, 1) if isinstance(pmdec, float) else str(pmdec),
            "parallax_mas": round(plx, 3) if isinstance(plx, float) else str(plx),
            "sp_type": sp,
        },
    }
    results.append(entry)

print("")
print("=" * 55)
print("Results")
print("=" * 55)
print("  Queried:        " + str(len(anchors)))
print("  Simbad found:   " + str(matched))
print("  Classified Psr: " + str(pulsar_classified))

print("")
print("--- Object Type Distribution ---")
for ot, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
    print("  " + ot.ljust(12) + ": " + str(cnt))

if discrepancies:
    print("")
    print("--- Discrepancies (catalog=pulsar, Simbad says otherwise) ---")
    for d in discrepancies[:15]:
        print("  " + d["anchor"].ljust(20) + " | Simbad: " + d["simbad"].ljust(30) + " (" + d["simbad_otype"] + ")")

# Parallax and proper motion summary
pm_hits = [r for r in results if r.get("simbad",{}).get("pmra_masyr","") and r["simbad"]["pmra_masyr"] not in ("","0.0")]
if pm_hits:
    print("")
    print("--- Proper Motions (first 10) ---")
    for r in pm_hits[:10]:
        s = r["simbad"]
        print("  " + r["anchor"].ljust(20) + " pmra=" + str(s["pmra_masyr"]) + " pmdec=" + str(s["pmdec_masyr"]))

plx_hits = [r for r in results if r.get("simbad",{}).get("parallax_mas","") and r["simbad"]["parallax_mas"] not in ("","nan","NaN")]
if plx_hits:
    print("")
    print("--- Parallax ---")
    for r in plx_hits[:5]:
        print("  " + r["anchor"].ljust(20) + " plx=" + str(r["simbad"]["parallax_mas"]) + " mas")

# Save
with open(OUTPUT, "w") as f:
    json.dump(results, f, indent=2)
print("")
print("Saved: " + OUTPUT)

# Report
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("# BlackHole Beacon - Simbad Cross-Comparison\n\n")
    f.write("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
    f.write("## Summary\n\n")
    f.write("- Queried: " + str(len(anchors)) + "\n")
    f.write("- Simbad found: " + str(matched) + "\n")
    f.write("- Classified as Pulsar: " + str(pulsar_classified) + "\n")
    f.write("- Discrepancies: " + str(len(discrepancies)) + "\n\n")
    f.write("## Object Types\n\n")
    f.write("| Type | Count |\n|------|-------|\n")
    for ot, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        f.write("| " + ot + " | " + str(cnt) + " |\n")
    if discrepancies:
        f.write("\n## Discrepancies\n\n")
        f.write("| Anchor | Expected | Simbad |\n|--------|----------|--------|\n")
        for d in discrepancies:
            f.write("| " + d["anchor"] + " | " + d["expected"] + " | " + d["simbad"] + " (" + d["simbad_otype"] + ") |\n")

print("Report: " + REPORT)
print("Done.")
