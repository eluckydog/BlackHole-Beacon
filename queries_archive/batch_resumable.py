"""BlackHole Beacon — Resumable Batch v1.0

Processes anchors one at a time with checkpoint save.
Auto-resumes from last saved checkpoint.
"""

import urllib.request, urllib.parse, ssl, json, csv, os, time, sys
import xml.etree.ElementTree as ET

# Config
RATE_LIMIT_S = 0.3
RADIUS_ARCSEC = 15
rad_deg = RADIUS_ARCSEC / 3600.0

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "https://irsa.ipac.caltech.edu/TAP/sync"
HEADERS = {"Accept": "application/x-votable+xml", "User-Agent": "BHBeacon/1.0"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR_DIR = os.path.join(ROOT, "catalog")
DATA_DIR = os.path.join(ROOT, "data")
CHECKPOINT = os.path.join(DATA_DIR, "_checkpoint.json")
RESULTS_FILE = os.path.join(DATA_DIR, "batch_all_results.json")

CATALOGS = {
    "2mass": {
        "table": "fp_psc",
        "cols": "designation, ra, dec, j_m, h_m, k_m, j_msigcom, h_msigcom, k_msigcom",
    },
    "wise": {
        "table": "allwise_p3as_psd",
        "cols": "designation, ra, dec, w1mpro, w2mpro, w3mpro, w4mpro, w1snr, w2snr",
    },
}

def tap_query(sql, timeout=30):
    params = urllib.parse.urlencode({"query": sql})
    url = f"{BASE}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return resp.read().decode("utf-8")

def parse_votable(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return [], f"XML parse: {e}"
    for info in root.iter():
        tag = info.tag.split("}")[-1]
        if tag == "INFO" and info.get("name") == "QUERY_STATUS":
            val = info.get("value", "")
            if "ERROR" in val.upper():
                return [], val
    for resource in root.iter():
        rtag = resource.tag.split("}")[-1]
        if rtag != "RESOURCE" or resource.get("type") != "results":
            continue
        table = None
        for child in resource:
            ct = child.tag.split("}")[-1]
            if ct == "TABLE":
                table = child
                break
        if table is None:
            continue
        fields = []
        for child in table:
            ct = child.tag.split("}")[-1]
            if ct == "FIELD":
                fields.append(child.get("name", ""))
        data_el = None
        for child in table:
            ct = child.tag.split("}")[-1]
            if ct == "DATA":
                data_el = child
                break
        if data_el is None:
            continue
        td_el = None
        for child in data_el:
            ct = child.tag.split("}")[-1]
            if ct == "TABLEDATA":
                td_el = child
                break
        if td_el is None:
            continue
        rows = []
        for tr in td_el:
            tt = tr.tag.split("}")[-1]
            if tt != "TR":
                continue
            vals = [td.text if td.text else "" for td in tr if td.tag.split("}")[-1] == "TD"]
            if vals:
                rows.append(dict(zip(fields, vals)))
        return rows, None
    return [], None

def load_anchors():
    anchors = []
    for fname, atype in [("psrcat_catalog.csv", "pulsar"),
                         ("bh_xrb_catalog.csv", "bh_xrb"),
                         ("smbh_catalog.csv", "smbh")]:
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
                except (ValueError, KeyError):
                    continue
    return anchors

def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, "r") as f:
            return json.load(f)
    return {"idx": 0, "results": []}

def save_checkpoint(cp):
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)

def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, float) and obj != obj:
        return None
    return obj

def main():
    anchors = load_anchors()
    total = len(anchors)
    print(f"BlackHole Beacon — Resumable Batch")
    print(f"Total anchors: {total}")

    cp = load_checkpoint()
    start = cp["idx"]
    results = cp["results"]
    print(f"Resuming from index {start} ({len(results)} already done)")

    stats = {"ok": 0, "err": 0, "matched": 0, "total_sources": 0}
    last_q = 0

    for i in range(start, total):
        a = anchors[i]
        pct = (i + 1) / total * 100

        # Rate limit
        now = time.time()
        if now - last_q < RATE_LIMIT_S:
            time.sleep(RATE_LIMIT_S - (now - last_q))
        last_q = time.time()

        sys.stdout.write(f"\r  [{i+1}/{total}] {pct:4.1f}% | {a['name'][:20]:20s} ")
        sys.stdout.flush()

        a_data = {"anchor": a, "matches": {}}
        all_ok = True

        for cat_name, ci in CATALOGS.items():
            try:
                sql = (f"SELECT TOP 5 {ci['cols']} FROM {ci['table']} "
                       f"WHERE CONTAINS(POINT('ICRS', ra, dec), "
                       f"CIRCLE('ICRS', {a['ra']}, {a['dec']}, {rad_deg}))=1")
                xml_text = tap_query(sql, timeout=25)
                rows, err = parse_votable(xml_text)
                stats["ok"] += 1
                if err:
                    stats["err"] += 1
                    all_ok = False
                elif rows:
                    stats["matched"] += 1
                    stats["total_sources"] += len(rows)
                    a_data["matches"][cat_name] = rows
            except Exception as e:
                stats["err"] += 1
                all_ok = False

        if a_data["matches"]:
            results.append(clean(a_data))

        # Checkpoint every 50
        if (i + 1) % 50 == 0:
            cp["idx"] = i + 1
            cp["results"] = results
            save_checkpoint(cp)

    # Final save
    cp["idx"] = total
    cp["results"] = results
    save_checkpoint(cp)

    # Aggregate
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - last_q + stats["ok"] * RATE_LIMIT_S
    print(f"\n\n{'='*55}")
    print(f"COMPLETE")
    print(f"{'='*55}")
    print(f"  Processed: {total}/{total}")
    print(f"  With matches: {len(results)}")
    print(f"  Queries: {stats['ok']} ok / {stats['err']} errors")
    print(f"  Matched anchors: {stats['matched']}")
    print(f"  Total sources: {stats['total_sources']}")
    print(f"  Saved: batch_all_results.json ({os.path.getsize(RESULTS_FILE):,} bytes)")

if __name__ == "__main__":
    main()
