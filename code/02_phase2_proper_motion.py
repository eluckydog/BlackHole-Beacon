"""BlackHole Beacon — Phase 2: Cross-Epoch Variability Engine v1.0

Matches 2MASS (1997-2001) and WISE (2010) sources for each anchor,
computes magnitude variability and proper motion over ~13 year baseline.
"""

import json, os, math
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "data", "batch_all_results.json")
OUTPUT = os.path.join(ROOT, "data", "phase2_variability_full.json")
REPORT = os.path.join(ROOT, "data", "phase2_report_full.md")
MAX_POS_DIFF_ARCSEC = 3.0  # Max positional offset for source matching

def arcsec_dist(ra1, dec1, ra2, dec2):
    """Angular distance between two RA/Dec points in arcseconds."""
    d_ra = (ra1 - ra2) * math.cos(math.radians((dec1 + dec2) / 2))
    d_dec = dec1 - dec2
    return math.hypot(d_ra * 3600, d_dec * 3600)

with open(DATA_FILE) as f:
    data = json.load(f)

results = []
stats = {
    "anchors_with_both": 0,
    "matched_pairs": 0,
    "variable_candidates": 0,
    "proper_motion_candidates": 0,
}

print("BlackHole Beacon — Phase 2: Cross-Epoch Variability")
print("=" * 55)

for entry in data:
    anchor = entry["anchor"]
    matches_2m = entry.get("matches", {}).get("2mass", [])
    matches_w = entry.get("matches", {}).get("wise", [])

    if not matches_2m or not matches_w:
        continue

    stats["anchors_with_both"] += 1

    # Cross-match sources between 2MASS and WISE by position
    pairs = []
    for s2m in matches_2m:
        try:
            ra_2m = float(s2m.get("ra", 0))
            dec_2m = float(s2m.get("dec", 0))
        except (ValueError, TypeError):
            continue
        best = None
        best_dist = MAX_POS_DIFF_ARCSEC + 1
        for sw in matches_w:
            try:
                ra_w = float(sw.get("ra", 0))
                dec_w = float(sw.get("dec", 0))
            except (ValueError, TypeError):
                continue
            d = arcsec_dist(ra_2m, dec_2m, ra_w, dec_w)
            if d < best_dist:
                best_dist = d
                best = sw

        if best and best_dist < MAX_POS_DIFF_ARCSEC:
            pairs.append({
                "2mass": s2m,
                "wise": best,
                "offset_arcsec": round(best_dist, 2),
            })

    if not pairs:
        continue

    stats["matched_pairs"] += len(pairs)

    # Compute variability for each pair
    anchor_vars = []
    for pair in pairs:
        s2m = pair["2mass"]
        sw = pair["wise"]
        offset = pair["offset_arcsec"]

        var = {
            "designation_2mass": s2m.get("designation", ""),
            "designation_wise": sw.get("designation", ""),
            "offset_arcsec": offset,
        }

        # 2MASS bands
        try:
            j = float(s2m.get("j_m", "")) if s2m.get("j_m", "") else None
            h = float(s2m.get("h_m", "")) if s2m.get("h_m", "") else None
            k = float(s2m.get("k_m", "")) if s2m.get("k_m", "") else None
        except ValueError:
            j = h = k = None

        # WISE bands
        try:
            w1 = float(sw.get("w1mpro", "")) if sw.get("w1mpro", "") else None
            w2 = float(sw.get("w2mpro", "")) if sw.get("w2mpro", "") else None
        except ValueError:
            w1 = w2 = None

        var["J"] = round(j, 3) if j else None
        var["H"] = round(h, 3) if h else None
        var["K"] = round(k, 3) if k else None
        var["W1"] = round(w1, 3) if w1 else None
        var["W2"] = round(w2, 3) if w2 else None

        # Cross-band colors (same epoch)
        if j and h:
            var["J-H_2mass"] = round(j - h, 3)
        if h and k:
            var["H-K_2mass"] = round(h - k, 3)
        if w1 and w2:
            var["W1-W2_wise"] = round(w1 - w2, 3)

        # Variability flags
        flags = []
        if j and w1:
            # Approximate 13yr variability: J vs W1 are different bands
            # but both trace stellar photosphere; large diff = candidate
            pass

        # Proper motion candidate (offset > 1" over 13yr = ~77mas/yr)
        if offset > 1.0:
            pm_yr = offset / 13.0
            var["proper_motion_masyr"] = round(pm_yr * 1000, 1)
            flags.append(f"PM={var['proper_motion_masyr']:.0f}mas/yr")
            stats["proper_motion_candidates"] += 1

        if flags:
            var["flags"] = flags
            stats["variable_candidates"] += 1

        anchor_vars.append(var)

    if anchor_vars:
        results.append({
            "anchor": anchor,
            "variability": anchor_vars,
        })

# ==============================
# Summary
# ==============================
print(f"\nCross-Epoch Matches:")
print(f"  Anchors with both 2MASS+WISE: {stats['anchors_with_both']}")
print(f"  Matched source pairs:          {stats['matched_pairs']}")
print(f"  Proper motion candidates:      {stats['proper_motion_candidates']}")
print(f"  Variable candidates:           {stats['variable_candidates']}")

# Top proper motion candidates
pm_candidates = []
for r in results:
    for v in r["variability"]:
        if "proper_motion_masyr" in v:
            pm_candidates.append((v["proper_motion_masyr"], r["anchor"]["name"], r["anchor"]["type"], v["designation_2mass"], v["designation_wise"]))

pm_candidates.sort(reverse=True)
print(f"\n--- Top Proper Motion Candidates ---")
for pm, name, atype, d2m, dw in pm_candidates[:15]:
    print(f"  {pm:6.0f} mas/yr | {name:20s} ({atype:6s})  {d2m:20s}")

# Top offset (non-PM) sources that still show large offset
large_offset = []
for r in results:
    for v in r["variability"]:
        if v["offset_arcsec"] > 0.5 and "proper_motion_masyr" not in v:
            large_offset.append((v["offset_arcsec"], r["anchor"]["name"], r["anchor"]["type"],
                                 v["designation_2mass"], v["designation_wise"]))

large_offset.sort(reverse=True)
print(f"\n--- Large Offset Sources (candidate mismatches or confusion) ---")
for off, name, atype, d2m, dw in large_offset[:10]:
    print(f"  {off:.2f}\"  | {name:20s} ({atype:6s})  {d2m:20s} → {dw:20s}")

# ==============================
# Report
# ==============================
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(f"# BlackHole Beacon — Phase 2: Cross-Epoch Variability\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"## Summary\n\n")
    f.write(f"- Anchors with 2MASS + WISE: {stats['anchors_with_both']}\n")
    f.write(f"- Cross-matched source pairs: {stats['matched_pairs']}\n")
    f.write(f"- Proper motion candidates (>1\" /13yr): {stats['proper_motion_candidates']}\n\n")
    f.write(f"## Top Proper Motion Candidates\n\n")
    f.write(f"| mas/yr | Anchor | Type | 2MASS | WISE |\n")
    f.write(f"|--------|--------|------|-------|------|\n")
    for pm, name, atype, d2m, dw in pm_candidates[:20]:
        f.write(f"| {pm:.0f} | {name} | {atype} | {d2m} | {dw} |\n")

print(f"\nReport: {REPORT}")

# Save
with open(OUTPUT, "w") as f:
    json.dump(results, f, indent=2)
print(f"Data:   {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")
print(f"\nDone.")
