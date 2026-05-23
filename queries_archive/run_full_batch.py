"""BlackHole Beacon — Phase 1: Full Sweep Runner

Scaled batch query for ALL 2,590 anchors across 2MASS + WISE.
Rate-limited to avoid IRSA throttling.
"""

import urllib.request, urllib.parse, ssl, json, csv, os, time, sys
import xml.etree.ElementTree as ET
from datetime import datetime

# -- Config --
BATCH_SIZE = 200         # anchors per chunk
RATE_LIMIT_S = 0.4       # seconds between queries (IRSA polite)
RADIUS_ARCSEC = 15
rad_deg = RADIUS_ARCSEC / 3600.0

# -- SSL --
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
        "cols": "designation, ra, dec, j_m, h_m, k_m, j_msigcom, h_msigcom, k_msigcom",
    },
    "wise": {
        "table": "allwise_p3as_psd",
        "cols": "designation, ra, dec, w1mpro, w2mpro, w3mpro, w4mpro, w1snr, w2snr",
    },
}

def tap_query_xml(sql, timeout=30):
    params = urllib.parse.urlencode({"query": sql})
    url = f"{BASE}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return resp.read().decode("utf-8")

def parse_votable(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return [], [], f"XML parse error: {e}"
    for info in root.iter():
        tag = info.tag.split("}")[-1]
        if tag == "INFO" and info.get("name") == "QUERY_STATUS":
            val = info.get("value", "")
            if "ERROR" in val.upper():
                return [], [], val
    for resource in root.iter():
        rtag = resource.tag.split("}")[-1]
        if rtag != "RESOURCE" or resource.get("type") != "results":
            continue
        table_el = None
        for child in resource:
            ctag = child.tag.split("}")[-1]
            if ctag == "TABLE":
                table_el = child
                break
        if table_el is None:
            continue
        fields = []
        for field_el in table_el:
            ftag = field_el.tag.split("}")[-1]
            if ftag == "FIELD":
                fields.append(field_el.get("name", ""))
        data_el = None
        for child in table_el:
            ctag = child.tag.split("}")[-1]
            if ctag == "DATA":
                data_el = child
                break
        if data_el is None:
            continue
        td_el = None
        for child in data_el:
            ctag = child.tag.split("}")[-1]
            if ctag == "TABLEDATA":
                td_el = child
                break
        if td_el is None:
            continue
        rows = []
        for tr_el in td_el:
            tr_tag = tr_el.tag.split("}")[-1]
            if tr_tag != "TR":
                continue
            vals = []
            for td in tr_el:
                td_tag = td.tag.split("}")[-1]
                if td_tag == "TD":
                    vals.append(td.text if td.text else "")
            if vals:
                rows.append(dict(zip(fields, vals)))
        return fields, rows, None
    return [], [], None

def load_anchors():
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
    return anchors

def clean_for_json(obj):
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    if isinstance(obj, float) and obj != obj:
        return None
    return obj

def run_batch(anchors, start, size, chunk_label):
    chunk = anchors[start:start + size]
    results = []
    t0 = time.time()
    stats = {cat: {"ok": 0, "err": 0, "matched": 0, "sources": 0} for cat in CATALOGS}
    last_q = 0

    print(f"\n{'='*55}")
    print(f"Chunk {chunk_label}: {len(chunk)} anchors (idx {start}-{start+len(chunk)-1})")
    print(f"{'='*55}")

    for i, a in enumerate(chunk):
        now = time.time()
        if now - last_q < RATE_LIMIT_S:
            time.sleep(RATE_LIMIT_S - (now - last_q))

        pct = (i + 1) / len(chunk) * 100
        sys.stdout.write(f"\r  [{i+1}/{len(chunk)}] {pct:4.0f}% | {a['name'][:18]:20s} ")
        sys.stdout.flush()
        last_q = time.time()

        a_results = {}
        for cat_name, ci in CATALOGS.items():
            try:
                sql = (f"SELECT TOP 5 {ci['cols']} FROM {ci['table']} "
                       f"WHERE CONTAINS(POINT('ICRS', ra, dec), "
                       f"CIRCLE('ICRS', {a['ra']}, {a['dec']}, {rad_deg}))=1")
                xml_text = tap_query_xml(sql)
                _, rows, err = parse_votable(xml_text)
                stats[cat_name]["ok"] += 1
                if err:
                    stats[cat_name]["err"] += 1
                elif rows:
                    stats[cat_name]["matched"] += 1
                    stats[cat_name]["sources"] += len(rows)
                    a_results[cat_name] = rows
            except Exception:
                stats[cat_name]["err"] += 1

        if a_results:
            results.append({"anchor": a, "matches": a_results})

    elapsed = time.time() - t0
    print(f"\n  Chunk done: {len(results)}/{len(chunk)} with matches in {elapsed:.0f}s")
    for cat_name in CATALOGS:
        s = stats[cat_name]
        print(f"  {cat_name}: {s['matched']}/{s['ok']} matched, {s['sources']} sources, {s['err']} errors")

    # Save chunk result
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"crossmatch_chunk{chunk_label}_{ts}.json"
    outpath = os.path.join(DATA_DIR, fname)
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(clean_for_json(results), f, indent=2, ensure_ascii=False)
    print(f"  Saved: {fname} ({os.path.getsize(outpath):,} bytes)")

    return elapsed, len(results)

if __name__ == "__main__":
    anchors = load_anchors()
    total = len(anchors)
    print(f"BlackHole Beacon — Full Sweep")
    print(f"Anchors: {total} (est. queries: {total * len(CATALOGS)} @ {RATE_LIMIT_S}s interval)")
    est_min = (total * len(CATALOGS) * RATE_LIMIT_S) / 60

    if total > 2000:
        # 分批跑，避免一次跑太久丢进度
        chunks_total = []
        chunk_num = 1
        for start in range(0, total, BATCH_SIZE):
            t, n = run_batch(anchors, start, BATCH_SIZE, str(chunk_num))
            chunks_total.append((chunk_num, n, t))
            chunk_num += 1
            # 每块之后 2 秒冷却
            if start + BATCH_SIZE < total:
                print("  Cooling 2s...")
                time.sleep(2)

        print(f"\n{'='*55}")
        print(f"ALL CHUNKS COMPLETE")
        print(f"{'='*55}")
        for cn, n, t in chunks_total:
            print(f"  Chunk {cn}: {n} matches in {t:.0f}s")
        print(f"  Total chunks: {len(chunks_total)}")
    else:
        run_batch(anchors, 0, BATCH_SIZE, "full")
