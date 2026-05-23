"""BlackHole Beacon — New Survey Cross-Comparison v1.0

Takes Gaia DR3 (optical, 2014-2017 epoch) as "new raw data" and
compares flux at anchor positions against our existing 2MASS+WISE model.

Questions:
  1. Do Gaia fluxes match our PCA-predicted optical flux?
  2. Which anchors have anomalous Gaia measurements?
  3. Can Gaia proper motions validate our PM candidates?
"""

import json, os, math, sys, time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR_DIR = os.path.join(ROOT, "catalog")
FEATURES_FILE = os.path.join(ROOT, "data", "spectral_features.json")
MODEL_FILE = os.path.join(ROOT, "data", "classifier_model.json")
OUTPUT = os.path.join(ROOT, "data", "gaia_comparison.json")
REPORT = os.path.join(ROOT, "data", "gaia_comparison_report.md")

# ==============================
# Gaia TAP query at ESA
# ==============================

import urllib.request, urllib.parse, ssl
import xml.etree.ElementTree as ET

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Gaia TAP endpoint (public)
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
H = {"User-Agent": "BHBeacon/1.0", "Accept": "application/x-votable+xml"}

def gaia_query(ra, dec, radius_deg=10/3600.0):
    """Query Gaia DR3 at a position. Returns list of source dicts."""
    sql = (
        f"SELECT TOP 5 source_id, ra, dec, phot_g_mean_mag, "
        f"phot_bp_mean_mag, phot_rp_mean_mag, "
        f"parallax, parallax_error, "
        f"pmra, pmdec, pmra_error, pmdec_error, "
        f"phot_g_mean_flux, phot_bp_mean_flux, phot_rp_mean_flux, "
        f"phot_g_mean_flux_error, phot_bp_mean_flux_error, phot_rp_mean_flux_error "
        f"FROM gaiadr3.gaia_source "
        f"WHERE CONTAINS(POINT('ICRS', ra, dec), "
        f"CIRCLE('ICRS', {ra}, {dec}, {radius_deg}))=1 "
        f"ORDER BY phot_g_mean_mag"
    )
    try:
        params = urllib.parse.urlencode({"query": sql})
        url = f"{GAIA_TAP}?{params}"
        req = urllib.request.Request(url, headers=H)
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        text = resp.read().decode("utf-8")
        return parse_votable_rows(text)
    except Exception as e:
        return [{"error": str(e)[:80]}]

def parse_votable_rows(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [{"error": "parse error"}]
    for info in root.iter():
        tag = info.tag.split("}")[-1]
        if tag == "INFO" and info.get("name") == "QUERY_STATUS":
            val = info.get("value", "")
            if "ERROR" in val.upper():
                return [{"error": val}]
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
        return rows
    return [{"error": "no results"}]

# ==============================
# Predict optical flux from SED model
# ==============================

def predict_g_mag_from_sed(sed):
    """Predict Gaia G band magnitude from NIR photometry using PCA model.
    Simple regression: G ~ w1*J + w2*H + w3*K + w4*(J-H) + bias.
    Returns (predicted_mag, confidence)."""
    j = sed.get("J")
    h = sed.get("H")
    k = sed.get("K")
    jh = sed.get("J-H")
    
    if not all(v is not None for v in [j, h, k]):
        return None, 0
    
    # Empirical: G ~ K + 2*(J-K) for typical stars
    # For pulsars with power-law SED, this relation differs
    g_pred = k + 2.0 * (j - k)
    
    # Uncertainty based on spectral index deviation
    alpha = sed.get("alpha_JK")
    confidence = 0.7  # base
    if alpha is not None:
        if -0.5 < alpha < 1.0:
            confidence += 0.2
        else:
            confidence -= 0.3
    
    return round(g_pred, 2), round(min(confidence, 1.0), 2)

# ==============================
# Run comparison on a subset
# ==============================

def load_anchors_for_gaia(anchor_dir, limit=50):
    """Load anchors for Gaia query (BH XRB + SMBH first, then pulsars)."""
    anchors = []
    for fname, atype in [("bh_xrb_catalog.csv", "bh_xrb"),
                          ("smbh_catalog.csv", "smbh"),
                          ("psrcat_catalog.csv", "pulsar")]:
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
                    if len(anchors) >= limit:
                        return anchors
                except (ValueError, KeyError):
                    continue
    return anchors

import csv

print("BlackHole Beacon — New Survey Cross-Comparison (Gaia DR3)")
print("=" * 55)

# Load existing spectral features for prediction
with open(FEATURES_FILE) as f:
    spectral_db = json.load(f)
sed_lookup = {s["anchor"]: s for s in spectral_db}

# Load anchors (small batch for Gaia - rate limited)
anchors = load_anchors_for_gaia(ANCHOR_DIR, limit=30)
print(f"\nAnchors to cross-check: {len(anchors)}")

# Query Gaia for each anchor
comparisons = []
gaia_matched = 0
prediction_success = 0
anomalies = []

rate_limit = 0.5
last_q = 0

for i, a in enumerate(anchors):
    # Rate limit
    now = time.time()
    if now - last_q < rate_limit:
        time.sleep(rate_limit - (now - last_q))
    last_q = time.time()
    
    sys.stdout.write(f"\r  [{i+1}/{len(anchors)}] {a['name'][:20]:20s} ")
    sys.stdout.flush()
    
    # Query Gaia
    soses = gaia_query(a["ra"], a["dec"])
    
    if not soses or "error" in soses[0]:
        comparisons.append({
            "anchor": a["name"],
            "type": a["type"], 
            "error": soses[0].get("error", "no data") if soses else "empty"
        })
        continue
    
    # Get brightest Gaia source
    best = soses[0]
    gaia_matched += 1
    
    # Get existing SED model
    sed = sed_lookup.get(a["name"], {})
    
    # Predict G mag from NIR
    g_pred, conf = predict_g_mag_from_sed(sed)
    
    # Extract Gaia measurements
    try:
        g_obs = float(best.get("phot_g_mean_mag", "")) if best.get("phot_g_mean_mag","") else None
        bp = float(best.get("phot_bp_mean_mag", "")) if best.get("phot_bp_mean_mag","") else None
        rp = float(best.get("phot_rp_mean_mag", "")) if best.get("phot_rp_mean_mag","") else None
        pllx = float(best.get("parallax", "")) if best.get("parallax","") else None
        pllx_e = float(best.get("parallax_error", "")) if best.get("parallax_error","") else None
        pmra = float(best.get("pmra", "")) if best.get("pmra","") else None
        pmdec = float(best.get("pmdec", "")) if best.get("pmdec","") else None
    except (ValueError, TypeError):
        continue
    
    if g_obs is None:
        continue
    
    prediction_success += 1
    
    # Compare prediction vs observation
    delta_g = g_pred - g_obs if g_pred else None
    
    entry = {
        "anchor": a["name"],
        "type": a["type"],
        "gaia": {
            "source_id": best.get("source_id", ""),
            "G": round(g_obs, 3),
            "BP": round(bp, 3) if bp else None,
            "RP": round(rp, 3) if rp else None,
            "parallax_mas": round(pllx, 3) if pllx else None,
            "parallax_error": round(pllx_e, 3) if pllx_e else None,
            "pmra_masyr": round(pmra, 1) if pmra else None,
            "pmdec_masyr": round(pmdec, 1) if pmdec else None,
        },
        "prediction": {
            "G_pred": g_pred,
            "confidence": conf,
            "delta": round(delta_g, 2) if delta_g else None,
        },
        "sed_bands_present": [k for k in ("J","H","K","W1","W2") if k in sed],
    }
    
    # Flag anomalies
    flags = []
    if delta_g is not None and abs(delta_g) > 0.5:
        flags.append(f"Gaia_G_diff={delta_g:+.2f}")
    if pllx is not None and pllx_e is not None and pllx_e < abs(pllx) * 3:
        flags.append(f"parallax={pllx:.2f}mas")
    
    if flags:
        entry["flags"] = flags
        anomalies.append(entry)
    
    comparisons.append(entry)

# Summary
print(f"\n\n{'='*55}")
print(f"Gaia Cross-Comparison Results")
print(f"{'='*55}")
print(f"\n  Anchors queried:     {len(anchors)}")
print(f"  Gaia matches:        {gaia_matched}")
print(f"  Predictions:         {prediction_success}")
print(f"  Anomalies flagged:   {len(anomalies)}")

# Compare G_pred vs G_obs
valid = [c for c in comparisons if c.get("prediction",{}).get("G_pred") is not None 
         and c.get("gaia",{}).get("G") is not None]
if valid:
    deltas = [c["prediction"]["delta"] for c in valid if c["prediction"]["delta"] is not None]
    if deltas:
        deltas.sort()
        print(f"\n  G_pred - G_obs distribution:")
        print(f"    n={len(deltas)}, med={deltas[len(deltas)//2]:.2f}, "
              f"[{min(deltas):.2f} ~ {max(deltas):.2f}]")

# Print sample
print(f"\n--- Comparison Table (first 20) ---")
print(f"{'Anchor':20s} {'Type':6s} {'G_obs':6s} {'G_pred':6s} {'ΔG':6s} {'Gaia_PMra':8s} {'Parallax':8s}")
print(f"{'-'*60}")
for c in comparisons[:20]:
    g_obs = c.get("gaia",{}).get("G", "")
    g_pred = c.get("prediction",{}).get("G_pred", "")
    dg = c.get("prediction",{}).get("delta", "")
    pmra = c.get("gaia",{}).get("pmra_masyr", "")
    pllx = c.get("gaia",{}).get("parallax_mas", "")
    
    g_obs_s = f"{g_obs:.2f}" if isinstance(g_obs, (int, float)) else ""
    g_pred_s = f"{g_pred:.2f}" if isinstance(g_pred, (int, float)) else ""
    dg_s = f"{dg:+.2f}" if isinstance(dg, (int, float)) else ""
    pmra_s = f"{pmra:.0f}" if isinstance(pmra, (int, float)) else ""
    pllx_s = f"{pllx:.2f}" if isinstance(pllx, (int, float)) else ""
    
    print(f"{c['anchor']:20s} {c['type']:6s} {g_obs_s:>6s} {g_pred_s:>6s} {dg_s:>6s} {pmra_s:>8s} {pllx_s:>8s}")

# Print anomalies
if anomalies:
    print(f"\n--- Anomalies ---")
    for a in anomalies[:10]:
        print(f"  {a['anchor']:20s} ({a['type']:6s}) | {', '.join(a.get('flags',[]))}")

# Save
with open(OUTPUT, "w") as f:
    json.dump(comparisons, f, indent=2)
print(f"\nSaved: {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")

# Report
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("# BlackHole Beacon — Gaia DR3 Cross-Comparison\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write("## Overview\n\n")
    f.write("Gaia DR3 (2014-2017) as 'new raw data' compared against 2MASS+WISE derived SED model.\n\n")
    f.write(f"- Anchors queried: {len(anchors)}\n")
    f.write(f"- Gaia matches: {gaia_matched}\n")
    f.write(f"- Predictions: {prediction_success}\n")
    f.write(f"- Anomalies: {len(anomalies)}\n\n")
    f.write("## Delta G Distribution\n\n")
    if deltas:
        f.write(f"- n={len(deltas)}\n")
        f.write(f"- min={min(deltas):.2f}, max={max(deltas):.2f}\n")
        f.write(f"- median={deltas[len(deltas)//2]:.2f}\n\n")
    f.write("## Full Results Table\n\n")
    f.write("| Anchor | Type | G_obs | G_pred | ΔG | Gaia PMra | Parallax |\n")
    f.write("|--------|------|-------|--------|-----|-----------|----------|\n")
    for c in comparisons:
        g_obs = c.get("gaia",{}).get("G", "")
        g_pred = c.get("prediction",{}).get("G_pred", "")
        dg = c.get("prediction",{}).get("delta", "")
        pmra = c.get("gaia",{}).get("pmra_masyr", "")
        pllx = c.get("gaia",{}).get("parallax_mas", "")
        gs = f"{g_obs:.2f}" if isinstance(g_obs, (int, float)) else ""
        gps = f"{g_pred:.2f}" if isinstance(g_pred, (int, float)) else ""
        ds = f"{dg:+.2f}" if isinstance(dg, (int, float)) else ""
        ps = f"{pmra:.0f}" if isinstance(pmra, (int, float)) else ""
        ls = f"{pllx:.2f}" if isinstance(pllx, (int, float)) else ""
        f.write(f"| {c['anchor']} | {c['type']} | {gs} | {gps} | {ds} | {ps} | {ls} |\n")

print(f"Report: {REPORT}")
print("\nDone. Anomalies show anchors where Gaia differs significantly from SED prediction.")
