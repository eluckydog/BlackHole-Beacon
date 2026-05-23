"""BlackHole Beacon — Phase 3: Candidate Scoring Engine v1.0

Scores each anchor-source pair on astrophysical interest using:
- Positional confidence (offset from anchor)
- Multi-band SED consistency
- Cross-epoch variability
- Proper motion detection
- Color anomalies
- Detection significance (brightness, SNR)
"""

import json, os, math
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHASE1 = os.path.join(ROOT, "data", "batch_all_results.json")
PHASE2 = os.path.join(ROOT, "data", "phase2_variability_full.json")
OUTPUT = os.path.join(ROOT, "data", "phase3_candidates_full.json")
REPORT = os.path.join(ROOT, "data", "phase3_report_full.md")

with open(PHASE1) as f:
    phase1 = json.load(f)

# Build Phase2 lookup: anchor_name -> variability list
phase2_lookup = {}
if os.path.exists(PHASE2):
    with open(PHASE2) as f:
        p2 = json.load(f)
    for r in p2:
        phase2_lookup[r["anchor"]["name"]] = r["variability"]

# ==============================
# Scoring functions
# ==============================

def calc_color_score(j, h, k, w1, w2):
    """Score based on SED reasonableness. 0=bad, 1=good, 2=interesting."""
    score = 0
    if j and h and k:
        jh = j - h
        hk = h - k
        # Typical stellar locus: J-H ~0.3-0.7, H-K ~0.1-0.3
        if 0.2 <= jh <= 1.0 and 0.0 <= hk <= 0.5:
            score += 1  # Normal star
        elif jh > 1.2 or hk > 0.6:
            score += 2  # Red/excess - interesting!
        elif jh < 0:
            score += 1  # Blue - could be foreground
    if w1 and w2:
        w12 = w1 - w2
        if -0.3 <= w12 <= 0.2:
            score += 1  # Normal photosphere
        elif w12 > 0.5:
            score += 2  # IR excess - interesting!
    return score

def calc_variability_score(p2_entry):
    """Score from proper motion and offset anomalies."""
    score = 0
    pm = p2_entry.get("proper_motion_masyr", 0)
    if pm > 100:
        score += 3  # High proper motion - very interesting
    elif pm > 50:
        score += 2
    elif pm > 20:
        score += 1
    offset = p2_entry.get("offset_arcsec", 0)
    if 0.5 < offset < 3.0 and pm < 10:
        score -= 1  # Offset without PM = likely mismatched
    return score

def calc_brightness_score(j, h, k, w1):
    """Prefer bright sources (easier follow-up)."""
    mags = [m for m in [j, h, k, w1] if m is not None]
    if not mags:
        return 0
    brightest = min(mags)
    if brightest < 10:
        return 3  # Very bright
    elif brightest < 13:
        return 2  # Bright
    elif brightest < 16:
        return 1  # Moderate
    return 0  # Faint

def calc_position_score(anchor_ra, anchor_dec, src_ra, src_dec):
    """Score based on proximity to anchor position."""
    d_ra = (anchor_ra - src_ra) * math.cos(math.radians((anchor_dec + src_dec) / 2))
    d_dec = anchor_dec - src_dec
    dist = math.hypot(d_ra * 3600, d_dec * 3600)
    if dist < 1:
        return 3  # Very close
    elif dist < 3:
        return 2  # Close
    elif dist < 8:
        return 1  # Moderate
    elif dist < 15:
        return 0  # Within search radius
    return -1  # Outside (shouldn't happen)

def get_anchor_type_score(atype):
    """Prefer BH XRB and SMBH over pulsars."""
    return {"bh_xrb": 2, "smbh": 1, "pulsar": 0}.get(atype, 0)

# ==============================
# Main scoring loop
# ==============================

candidates = []
print("BlackHole Beacon — Phase 3: Candidate Scoring")
print("=" * 55)

for entry in phase1:
    anchor = entry["anchor"]
    matches = entry.get("matches", {})
    p2_vars = phase2_lookup.get(anchor["name"], [])
    p2_by_2mass = {}
    for v in p2_vars:
        p2_by_2mass[v["designation_2mass"]] = v

    for cat_name in ("2mass", "wise"):
        for src in matches.get(cat_name, []):
            try:
                src_ra = float(src.get("ra", 0))
                src_dec = float(src.get("dec", 0))
            except (ValueError, TypeError):
                continue

            # Extract magnitudes
            try:
                j = float(src.get("j_m","")) if src.get("j_m","") else None
                h = float(src.get("h_m","")) if src.get("h_m","") else None
                k = float(src.get("k_m","")) if src.get("k_m","") else None
            except ValueError:
                j = h = k = None
            try:
                w1 = float(src.get("w1mpro","")) if src.get("w1mpro","") else None
                w2 = float(src.get("w2mpro","")) if src.get("w2mpro","") else None
            except ValueError:
                w1 = w2 = None

            # Find corresponding Phase 2 entry
            desig = src.get("designation", "")
            p2_entry = p2_by_2mass.get(desig, {})

            # Compute scores
            pos_score = calc_position_score(anchor["ra"], anchor["dec"], src_ra, src_dec)
            col_score = calc_color_score(j, h, k, w1, w2)
            var_score = calc_variability_score(p2_entry)
            bri_score = calc_brightness_score(j, h, k, w1)
            type_score = get_anchor_type_score(anchor["type"])
            pm = p2_entry.get("proper_motion_masyr", 0)

            # Total score (weighted)
            total = (pos_score * 2.0 + col_score * 1.5 + var_score * 2.0 +
                     bri_score * 1.0 + type_score * 2.0)
            total = round(total, 1)

            # Only include interesting candidates
            if total >= 4.0 or "proper_motion_masyr" in p2_entry:
                candidates.append({
                    "anchor": anchor["name"],
                    "type": anchor["type"],
                    "catalog": cat_name,
                    "designation": desig,
                    "ra": round(src_ra, 6),
                    "dec": round(src_dec, 6),
                    "J": j, "H": h, "K": k,
                    "W1": w1, "W2": w2,
                    "proper_motion_masyr": pm,
                    "offset_arcsec": p2_entry.get("offset_arcsec", 0),
                    "scores": {
                        "position": pos_score,
                        "color": col_score,
                        "variability": var_score,
                        "brightness": bri_score,
                        "anchor_type": type_score,
                        "total": total,
                    }
                })

# Sort by total score descending
candidates.sort(key=lambda c: c["scores"]["total"], reverse=True)

# Summary
print(f"\nTotal candidates scored: {len(candidates)}")
top_bh = [c for c in candidates if c["type"] in ("bh_xrb", "smbh")]
print(f"BH/SMBH candidates: {len(top_bh)}")
pm_cands = [c for c in candidates if c["proper_motion_masyr"] > 0]
print(f"With proper motion:   {len(pm_cands)}")

# Print top 30
print(f"\n--- Top 30 Candidates ---")
print(f"{'Rank':>4s} {'Score':>5s} {'Type':>8s} {'ProperMotion':>12s} {'Anchor':>20s} {'Designation':>20s}")
print(f"{'─'*72}")
for i, c in enumerate(candidates[:30]):
    pm_str = f"{c['proper_motion_masyr']:.0f}mas" if c['proper_motion_masyr'] else ""
    print(f"{i+1:4d} {c['scores']['total']:5.1f} {c['type']:>8s} {pm_str:>12s} {c['anchor']:>20s} {c['designation']:>20s}")

# ==============================
# Generate report
# ==============================
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(f"# BlackHole Beacon — Phase 3: Candidate Ranking\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"## Summary\n\n")
    f.write(f"- Total candidates scored: {len(candidates)}\n")
    f.write(f"- BH/SMBH anchors: {len(top_bh)}\n")
    f.write(f"- With proper motion: {len(pm_cands)}\n\n")
    f.write(f"## Top 50 Candidates\n\n")
    f.write(f"| Rank | Score | Type | PM (mas/yr) | Anchor | Designation |\n")
    f.write(f"|------|-------|------|-------------|--------|-------------|\n")
    for i, c in enumerate(candidates[:50]):
        pm_str = f"{c['proper_motion_masyr']:.0f}" if c['proper_motion_masyr'] else ""
        f.write(f"| {i+1} | {c['scores']['total']} | {c['type']} | {pm_str} | {c['anchor']} | {c['designation']} |\n")
    f.write(f"\n## Score Distribution\n\n")
    scores = [c["scores"]["total"] for c in candidates]
    if scores:
        f.write(f"- Min: {min(scores):.1f}\n")
        f.write(f"- Median: {sorted(scores)[len(scores)//2]:.1f}\n")
        f.write(f"- Max: {max(scores):.1f}\n\n")
    f.write(f"\n## Score Components\n\n")
    f.write(f"- **Position**: proximity to anchor position (0-3)\n")
    f.write(f"- **Color**: SED anomaly detection (0-4)\n")
    f.write(f"- **Variability**: proper motion, cross-epoch changes (0-3)\n")
    f.write(f"- **Brightness**: follow-up feasibility (0-3)\n")
    f.write(f"- **Anchor Type**: BH XRB bonus (0-2)\n")
    f.write(f"- **Total**: position×2 + color×1.5 + variability×2 + brightness×1 + type×2\n")

# Save
with open(OUTPUT, "w") as f:
    json.dump(candidates, f, indent=2)
print(f"\nData:   {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")
print(f"Report: {REPORT}")
print(f"\nDone.")
