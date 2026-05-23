"""BlackHole Beacon — Multi-Archive Query Engine v1.0

Adds IRAS (1983 infrared), ZTF (2018+ optical), and ROSAT (1990-1999 X-ray)
to the existing cross-match pipeline. Modular: each archive is standalone.

Usage:
  python queries/multi_archive.py [--archive iras|ztf|rosat|all] [--batch N]
"""

import urllib.request, urllib.parse, ssl, json, csv, os, time, sys
import xml.etree.ElementTree as ET

# ==============================
# Archive definitions
# ==============================

ARCHIVES = {}

ARCHIVES["iras"] = {
    "name": "IRAS",
    "desc": "IRAS Point Source Catalog (12/25/60/100 um, 1983)",
    "tables": ["iras_psc"],
    "columns": "ra, dec, f12, f25, f60, f100, qual, id",
    "cols_verbose": ["ra", "dec", "f12", "f25", "f60", "f100", "qual", "id"],
    "endpoint": "https://irsa.ipac.caltech.edu/TAP/sync",
    "radius": 30,  # IRAS has lower resolution, use 30"
}

ARCHIVES["ztf"] = {
    "name": "ZTF",
    "desc": "Zwicky Transient Facility DR22 (optical g/r/i, 2018-present)",
    "tables": ["ztf_dr22_objects_sci"],
    "columns": "ra, dec, gmag, rmag, imag, ng, nr, ni",
    "cols_verbose": ["ra", "dec", "gmag", "rmag", "imag", "ng", "nr", "ni"],
    "endpoint": "https://irsa.ipac.caltech.edu/TAP/sync",
    "radius": 5,  # ZTF has good resolution
}

ARCHIVES["rosat"] = {
    "name": "ROSAT",
    "desc": "ROSAT All-Sky Survey (X-ray 0.1-2.4 keV, 1990-1999)",
    "tables": ["rosat"],
    "columns": "ra, dec, cnt_rate, hr1, hr2, src_id",
    "cols_verbose": ["ra", "dec", "cnt_rate", "hr1", "hr2", "src_id"],
    "endpoint": "https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync",
    "radius": 30,  # ROSAT positional uncertainty
}

# ==============================
# Core TAP query (VOTable XML)
# ==============================

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def tap_query(endpoint, sql, timeout=30):
    params = urllib.parse.urlencode({"query": sql})
    url = f"{endpoint}?{params}"
    headers = {"Accept": "application/x-votable+xml", "User-Agent": "BHBeacon/1.0"}
    req = urllib.request.Request(url, headers=headers)
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

def query_archive(archive_name, ra, dec, timeout=25):
    """Query one archive at a position, return list of source dicts."""
    arch = ARCHIVES[archive_name]
    rad = arch["radius"] / 3600.0
    table = arch["tables"][0]
    cols = arch["columns"]

    # Try primary table first
    sql = (f"SELECT {cols} FROM {table} "
           f"WHERE CONTAINS(POINT('ICRS', ra, dec), "
           f"CIRCLE('ICRS', {ra}, {dec}, {rad}))=1 "
           f"ORDER BY ra")

    try:
        xml_text = tap_query(arch["endpoint"], sql, timeout=timeout)
        rows, err = parse_votable(xml_text)
        if err:
            return [], err
        return rows, None
    except Exception as e:
        # Try fallback table if primary fails
        if len(arch["tables"]) > 1:
            try:
                sql2 = (f"SELECT {cols} FROM {arch['tables'][1]} "
                       f"WHERE CONTAINS(POINT('ICRS', ra, dec), "
                       f"CIRCLE('ICRS', {ra}, {dec}, {rad}))=1")
                xml_text = tap_query(arch["endpoint"], sql2, timeout=timeout)
                rows, err = parse_votable(xml_text)
                if err:
                    return [], err
                return rows, None
            except Exception:
                return [], str(e)
        return [], str(e)

# ==============================
# CLI / batch runner
# ==============================

def load_anchors(anchor_dir, limit=0):
    anchors = []
    for fname, atype in [("psrcat_catalog.csv", "pulsar"),
                          ("bh_xrb_catalog.csv", "bh_xrb"),
                          ("smbh_catalog.csv", "smbh")]:
        fp = os.path.join(anchor_dir, fname)
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
    if limit:
        anchors = anchors[:limit]
    return anchors

def run_scan(archives_to_run, anchors, rate_limit=0.5, out_dir="data", label=""):
    """Run scan for specified archives across anchors."""
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUT_DIR = os.path.join(ROOT, out_dir)
    os.makedirs(OUT_DIR, exist_ok=True)

    for arch_name in archives_to_run:
        if arch_name not in ARCHIVES:
            print(f"Unknown archive: {arch_name}")
            continue
        arch = ARCHIVES[arch_name]
        print(f"\n{'='*50}")
        print(f"Scanning {arch['name']}: {arch['desc']}")
        print(f"Radius: {arch['radius']}\" | Anchors: {len(anchors)}")
        print(f"{'='*50}")

        results = []
        t0 = time.time()
        last_q = 0

        for i, a in enumerate(anchors):
            now = time.time()
            if now - last_q < rate_limit:
                time.sleep(rate_limit - (now - last_q))
            last_q = time.time()

            sys.stdout.write(f"\r  [{i+1}/{len(anchors)}] {a['name'][:20]:20s}")
            sys.stdout.flush()

            rows, err = query_archive(arch_name, a["ra"], a["dec"])
            if rows:
                results.append({"anchor": a, "sources": rows, "archive": arch_name})

        ts = time.strftime("%Y%m%d_%H%M%S")
        suf = f"_{label}" if label else ""
        out_name = f"crossmatch_{arch_name}{suf}_{ts}.json"
        out_path = os.path.join(OUT_DIR, out_name)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)

        elapsed = time.time() - t0
        print(f"\n  Done: {len(results)} anchors with detections in {elapsed:.0f}s")
        print(f"  Saved: {out_name} ({os.path.getsize(out_path):,} bytes)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", choices=["iras", "ztf", "rosat", "all"], default="all")
    parser.add_argument("--batch", type=int, default=50, help="Anchors to process")
    args = parser.parse_args()

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ANCHOR_DIR = os.path.join(ROOT, "catalog")

    archives = ["iras", "ztf", "rosat"] if args.archive == "all" else [args.archive]
    anchors = load_anchors(ANCHOR_DIR, limit=args.batch)

    print(f"Multi-Archive Query Engine v1.0")
    print(f"Archives: {', '.join(archives)}")
    print(f"Anchors: {len(anchors)} (first {args.batch})")
    print()

    run_scan(archives, anchors, out_dir="data", label=f"b{args.batch}")
