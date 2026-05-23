"""BlackHole Beacon -- Phase 1: IRSA Batch Cross-Match Engine v1.0

Queries 2MASS and WISE for each anchor position via cone search.
IRSA TAP /sync endpoint. Parses VOTable XML (format=votable) -- works
for all catalogs including spatial queries that refuse JSON format.
"""

import urllib.request, urllib.parse, ssl, json, csv, os, time, sys
import xml.etree.ElementTree as ET
from datetime import datetime

# -- SSL (IRSA cert issues in some environments) --
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "https://irsa.ipac.caltech.edu/TAP/sync"
HEADERS = {"Accept": "application/x-votable+xml", "User-Agent": "BHBeacon/1.0"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR_DIR = os.path.join(ROOT, "catalog")
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CATALOGS = {
    "2mass": {
        "table": "fp_psc",
        "desc": "2MASS PSC",
        "cols": "designation, ra, dec, j_m, h_m, k_m, j_msigcom, h_msigcom, k_msigcom",
        "epoch": "1997-2001",
    },
    "wise": {
        "table": "allwise_p3as_psd",
        "desc": "AllWISE",
        "cols": "designation, ra, dec, w1mpro, w2mpro, w3mpro, w4mpro, w1snr, w2snr",
        "epoch": "2010",
    },
    "iras": {
        "table": "iras.psc",
        "desc": "IRAS PSC",
        "cols": "name, ra, dec, f12, f25, f60, f100, q12, q25, q60, q100",
        "epoch": "1983",
    },
}

RADIUS_ARCSEC = 15
rad_deg = RADIUS_ARCSEC / 3600.0

# ============================================================
# VOTable XML parser
# ============================================================

def tap_query_xml(sql, timeout=60):
    """Execute IRSA TAP sync query, return VOTable XML string."""
    params = urllib.parse.urlencode({"query": sql})
    url = f"{BASE}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    raw = resp.read()
    text = raw.decode("utf-8")
    return text

def parse_votable(xml_text):
    """Parse VOTable XML, return (fields, rows, error_msg).
    
    fields: list of column names
    rows:   list of dicts [{col: val}, ...]
    error_msg: str or None (if QUERY_STATUS=ERROR)
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return [], [], f"XML parse error: {e}"

    ns = {"v": "http://www.ivoa.net/xml/VOTable/v1.3"}
    # Also try prefix-less
    def findall(el, tag):
        r = el.findall(tag)
        if not r:
            r = el.findall(f"{{http://www.ivoa.net/xml/VOTable/v1.3}}{tag}")
        return r

    # Check for error INFO
    for info in root.iter():
        tag = info.tag.split("}")[-1] if "}" in info.tag else info.tag
        if tag == "INFO" and info.get("name") == "QUERY_STATUS":
            val = info.get("value", "")
            if "ERROR" in val.upper():
                return [], [], val

    # Find first RESOURCE with type="results"
    for resource in findall(root, "RESOURCE"):
        if resource.get("type") != "results":
            continue

        table_el = resource.find("TABLE")
        if table_el is None:
            # TABLE might be in namespace
            for ns_uri in ["{http://www.ivoa.net/xml/VOTable/v1.3}TABLE"]:
                table_el = resource.find(ns_uri)
                if table_el is not None:
                    break
        if table_el is None:
            continue

        # Fields
        fields = []
        for field_el in findall(table_el, "FIELD"):
            name = field_el.get("name", "")
            if not name:
                # namespace fallback
                for k, v in field_el.attrib.items():
                    if "name" in k:
                        name = v
                        break
            fields.append(name)

        # Data -> TABLEDATA -> TR
        data_el = table_el.find("DATA")
        if data_el is None:
            for ns_uri in ["{http://www.ivoa.net/xml/VOTable/v1.3}DATA"]:
                data_el = table_el.find(ns_uri)
                if data_el is not None:
                    break
        if data_el is None:
            continue

        td_el = data_el.find("TABLEDATA")
        if td_el is None:
            for ns_uri in ["{http://www.ivoa.net/xml/VOTable/v1.3}TABLEDATA"]:
                td_el = data_el.find(ns_uri)
                if td_el is not None:
                    break
        if td_el is None:
            continue

        rows = []
        for tr_el in findall(td_el, "TR"):
            vals = []
            for td in findall(tr_el, "TD"):
                vals.append(td.text if td.text else "")
            if vals:
                rows.append(dict(zip(fields, vals)))

        return fields, rows, None

    # No results resource found
    return [], [], None

# ============================================================
# Load anchors
# ============================================================

print("=" * 55)
print(f"BlackHole Beacon | IRSA VOTable Engine")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Catalogs: {', '.join(f'{c}({v['epoch']})' for c, v in CATALOGS.items())}")
print(f"Radius: {RADIUS_ARCSEC}\" | Format: VOTable XML")
print("=" * 55)

anchors = []
for fname, atype in [("psrcat_catalog.csv", "pulsar"),
                      ("bh_xrb_catalog.csv", "bh_xrb"),
                      ("smbh_catalog.csv", "smbh")]:
    fpath = os.path.join(ANCHOR_DIR, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, encoding="utf-8") as f:
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
            except (ValueError, KeyError):
                continue

print(f"\nLoaded {len(anchors)} anchors\n")
sys.stdout.flush()

# ============================================================
# Connectivity test
# ============================================================
print("--- Connectivity test ---")
try:
    xml_text = tap_query_xml("SELECT TOP 1 ra, dec FROM fp_psc")
    flds, rows, err = parse_votable(xml_text)
    if err:
        print(f"  fp_psc: FAIL ({err[:60]})")
    else:
        print(f"  fp_psc: OK ({len(rows)} row, {len(flds)} fields)")

    xml_text2 = tap_query_xml("SELECT TOP 1 ra, dec FROM allwise_p3as_psd")
    flds2, rows2, err2 = parse_votable(xml_text2)
    if err2:
        print(f"  allwise: FAIL ({err2[:60]})")
    else:
        print(f"  allwise: OK ({len(rows2)} row, {len(flds2)} fields)")

    xml_text3 = tap_query_xml("SELECT TOP 1 ra, dec FROM iras.psc")
    flds3, rows3, err3 = parse_votable(xml_text3)
    if err3:
        print(f"  iras.psc: FAIL ({err3[:60]})")
    else:
        print(f"  iras.psc: OK ({len(rows3)} row, {len(flds3)} fields)")

    if not err and not err2:
        print("  => VOTable XML parsing ready\n")
    else:
        print("  => WARNING: some catalogs unavailable\n")
except Exception as e:
    print(f"  FAIL: {e}\n")
    sys.exit(1)

sys.stdout.flush()

# ============================================================
# Batch query (first 5 anchors)
# ============================================================

BATCH = 5
results = []
stats = {cat: {"ok": 0, "err": 0, "matches": 0, "sources": 0} for cat in CATALOGS}
t_start = time.time()

for idx in range(min(BATCH, len(anchors))):
    a = anchors[idx]
    sys.stdout.write(f"[{idx+1}/{BATCH}] {a['name']:20s} {a['type']:10s}")
    sys.stdout.flush()
    t0 = time.time()
    anchor_matches = {}

    for cat_name, cat_info in CATALOGS.items():
        try:
            sql = (f"SELECT TOP 3 {cat_info['cols']} FROM {cat_info['table']} "
                   f"WHERE CONTAINS(POINT('ICRS', ra, dec), "
                   f"CIRCLE('ICRS', {a['ra']}, {a['dec']}, {rad_deg}))=1")

            xml_text = tap_query_xml(sql, timeout=30)
            flds, rows, err = parse_votable(xml_text)

            stats[cat_name]["ok"] += 1
            if err:
                stats[cat_name]["err"] += 1
                sys.stdout.write(f"  {cat_name}:ERR({err[:30]})")
            elif rows:
                stats[cat_name]["matches"] += 1
                stats[cat_name]["sources"] += len(rows)
                anchor_matches[cat_name] = rows
                # Brightest mag
                mag_key = "j_m" if cat_name == "2mass" else "w1mpro"
                mags = [float(r.get(mag_key, "99")) for r in rows if r.get(mag_key) and r.get(mag_key) != ""]
                best = f"{min(mags):.1f}" if mags else "?"
                sys.stdout.write(f"  {cat_name}:{len(rows)}(best={best})")
            else:
                pass  # no match -- normal

        except Exception as e:
            sys.stdout.write(f"  {cat_name}:FAIL({str(e)[:30]})")

    dt = time.time() - t0
    sys.stdout.write(f"  [{dt:.1f}s]\n")
    sys.stdout.flush()

    if anchor_matches:
        results.append({"anchor": a, "matches": anchor_matches})

# ============================================================
# Summary
# ============================================================

total_t = time.time() - t_start
print(f"\n{'='*55}")
print(f"Phase 1a Results ({BATCH} anchors, {total_t:.0f}s)")
print("=" * 55)

anchors_with_data = len(results)
print(f"  Anchors with IR data: {anchors_with_data}/{BATCH}")

for cat_name, cat_info in CATALOGS.items():
    s = stats[cat_name]
    print(f"  {cat_name:8s} ({cat_info['desc']:14s}): {s['matches']}/{s['ok']} matched, "
          f"{s['sources']} sources, {s['err']} errors")

# Save
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
outpath = os.path.join(DATA_DIR, f"crossmatch_v1_{BATCH}a_{ts}.json")

def clean_for_json(obj):
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    if isinstance(obj, float) and obj != obj:
        return None
    return obj

with open(outpath, "w", encoding="utf-8") as f:
    json.dump(clean_for_json(results), f, indent=2, ensure_ascii=False)
print(f"\n  Saved: {os.path.basename(outpath)} ({os.path.getsize(outpath):,} bytes)")

# Show sample
if results:
    print(f"\n  --- Sample detections ---")
    for r_entry in results[:5]:
        a = r_entry["anchor"]
        for cat, rows in r_entry["matches"].items():
            if rows:
                mag_key = "j_m" if cat == "2mass" else "w1mpro"
                mags = [r.get(mag_key, "?") for r in rows[:3]]
                print(f"  {a['name']} ({a['type']}): {cat} = {mags}")

print(f"\n  Batch complete. Run with BATCH=100 for full sweep.")