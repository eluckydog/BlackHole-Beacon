"""BlackHole Beacon — Spectral Feature Extractor v1.0

For each anchor, collects all available multi-band photometry and
extracts spectral features: indices, colors, SED classification flags.
"""

import json, os, math
from datetime import datetime
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHASE1 = os.path.join(ROOT, "data", "crossmatch_phase1_v1.json")
PHASE2 = os.path.join(ROOT, "data", "phase2_variability.json")
OUTPUT = os.path.join(ROOT, "data", "spectral_features.json")
REPORT = os.path.join(ROOT, "data", "spectral_report.md")

with open(PHASE1) as f:
    phase1 = json.load(f)

# Build anchor lookup
anchors_data = {}
for entry in phase1:
    name = entry["anchor"]["name"]
    if name not in anchors_data:
        anchors_data[name] = {"anchor": entry["anchor"], "2mass": [], "wise": []}
    for cat in ("2mass", "wise"):
        if cat in entry.get("matches", {}):
            anchors_data[name][cat].extend(entry["matches"][cat])

# Phase 2 lookup
phase2_vars = {}
if os.path.exists(PHASE2):
    with open(PHASE2) as f:
        p2 = json.load(f)
    for r in p2:
        phase2_vars[r["anchor"]["name"]] = r["variability"]

# ==============================
# Spectral indices
# ==============================

# Wavelengths in microns
BANDS = {
    "g": 0.48, "r": 0.62, "i": 0.76,
    "J": 1.235, "H": 1.662, "K": 2.159,
    "W1": 3.368, "W2": 4.618, "W3": 12.082, "W4": 22.194,
    "IRAS12": 12, "IRAS25": 25, "IRAS60": 60, "IRAS100": 100,
}

def spectral_index(flux1, lam1, flux2, lam2):
    """Compute spectral index alpha: f_nu ~ nu^alpha.
    Given fluxes and wavelengths (flux ~ lambda^? actually for f_nu)."""
    if flux1 <= 0 or flux2 <= 0:
        return None
    nu1 = 2.998e14 / (lam1 * 1e-6)  # Hz
    nu2 = 2.998e14 / (lam2 * 1e-6)
    return math.log(flux1 / flux2) / math.log(nu1 / nu2)

def mag_to_flux(mag, band):
    """Rough flux conversion for spectral index estimation.
    Zero points from various surveys, approximate."""
    zp = {
        "g": 3631, "r": 3631, "i": 3631,  # AB mag
        "J": 1594, "H": 1024, "K": 667,   # Vega -> Jy
        "W1": 309.54, "W2": 171.79, "W3": 31.67, "W4": 8.36,
    }
    zp_val = zp.get(band, 1000)
    return zp_val * 10 ** (-mag / 2.5)  # Jy

def color_temp(color, band1, band2):
    """Rough color temperature in K."""
    if color is None:
        return None
    lam1 = BANDS.get(band1, 1)
    lam2 = BANDS.get(band2, 1)
    if lam1 == lam2:
        return None
    # Wien approximation: T = hc/k * (1/l2 - 1/l1) / ln(f1/f2)
    # For a blackbody: ln(f_nu1/f_nu2) = (3+alpha) * ln(nu1/nu2)
    # where alpha = d(ln f)/d(ln nu)
    return None  # Placeholder - too rough for now

# ==============================
# Process each anchor
# ==============================

spectral_db = []
n_with_2mass = 0
n_with_wise = 0
n_with_both = 0

for name, ad in anchors_data.items():
    a = ad["anchor"]
    s2m = ad["2mass"]
    sw = ad["wise"]

    if s2m:
        n_with_2mass += 1
    if sw:
        n_with_wise += 1
    if s2m and sw:
        n_with_both += 1

    # Best source per catalog (brightest)
    def best_mag(srcs, mag_key):
        best = None
        best_val = 99
        for s in srcs:
            try:
                v = float(s.get(mag_key, 99))
                if v < best_val:
                    best_val = v
                    best = s
            except (ValueError, TypeError):
                pass
        return best

    best_2m = best_mag(s2m, "j_m")
    best_w = best_mag(sw, "w1mpro")

    # Build SED vector
    sed = {"anchor": name, "type": a["type"], "ra": a["ra"], "dec": a["dec"]}

    # 2MASS
    if best_2m:
        try:
            sed["J"] = float(best_2m.get("j_m"))
            sed["H"] = float(best_2m.get("h_m"))
            sed["K"] = float(best_2m.get("k_m"))
        except:
            pass

    # WISE
    if best_w:
        try:
            sed["W1"] = float(best_w.get("w1mpro"))
            sed["W2"] = float(best_w.get("w2mpro"))
            w3 = best_w.get("w3mpro", "")
            w4 = best_w.get("w4mpro", "")
            if w3: sed["W3"] = float(w3)
            if w4: sed["W4"] = float(w4)
        except:
            pass

    # Colors
    if "J" in sed and "H" in sed:
        sed["J-H"] = round(sed["J"] - sed["H"], 3)
    if "H" in sed and "K" in sed:
        sed["H-K"] = round(sed["H"] - sed["K"], 3)
    if "W1" in sed and "W2" in sed:
        sed["W1-W2"] = round(sed["W1"] - sed["W2"], 3)
    if "W2" in sed and "W3" in sed:
        sed["W2-W3"] = round(sed["W2"] - sed["W3"], 3)

    # Spectral indices (optical-NIR, NIR-MIR)
    if "J" in sed and "K" in sed:
        f_j = mag_to_flux(sed["J"], "J")
        f_k = mag_to_flux(sed["K"], "K")
        alpha = spectral_index(f_j, BANDS["J"], f_k, BANDS["K"])
        if alpha is not None:
            sed["alpha_JK"] = round(alpha, 3)

    if "W1" in sed and "W2" in sed:
        f_w1 = mag_to_flux(sed["W1"], "W1")
        f_w2 = mag_to_flux(sed["W2"], "W2")
        alpha = spectral_index(f_w1, BANDS["W1"], f_w2, BANDS["W2"])
        if alpha is not None:
            sed["alpha_W12"] = round(alpha, 3)

    if "J" in sed and "W1" in sed:
        f_j = mag_to_flux(sed["J"], "J")
        f_w1 = mag_to_flux(sed["W1"], "W1")
        alpha = spectral_index(f_j, BANDS["J"], f_w1, BANDS["W1"])
        if alpha is not None:
            sed["alpha_JW1"] = round(alpha, 3)

    # Variability features from Phase 2
    pv = phase2_vars.get(name, [])
    if pv:
        max_pm = max((v.get("proper_motion_masyr", 0) for v in pv), default=0)
        if max_pm:
            sed["max_proper_motion_masyr"] = round(max_pm, 1)

        max_offset = max((v.get("offset_arcsec", 0) for v in pv), default=0)
        if max_offset:
            sed["max_offset_arcsec"] = round(max_offset, 2)

    # Classification flags
    flags = []

    # Red IR excess (WISE)
    w12 = sed.get("W1-W2")
    if w12 is not None and w12 > 0.5:
        flags.append("IR_EXCESS_WISE")
    if w12 is not None and w12 > 1.0:
        flags.append("STRONG_IR_EXCESS")

    # Red optical-NIR
    jh = sed.get("J-H")
    hk = sed.get("H-K")
    if jh and hk and jh > 1.0 and hk > 0.3:
        flags.append("RED_ANOMALY")

    # Blue NIR (possible accretion?)
    if jh is not None and jh < 0.1:
        flags.append("BLUE_NIR")

    # Bright sources
    bright = min((sed.get(k, 99) for k in ("J", "H", "K", "W1") if k in sed), default=99)
    if bright < 10:
        flags.append("BRIGHT")
    elif bright < 14:
        flags.append("MODERATE")

    # Multi-band coverage
    bands_present = [k for k in ("J","H","K","W1","W2","W3","W4") if k in sed]
    if len(bands_present) >= 5:
        flags.append("FULL_SED")

    if flags:
        sed["flags"] = flags

    spectral_db.append(sed)

# ==============================
# Summary
# ==============================
print("BlackHole Beacon — Spectral Feature Extractor")
print("=" * 55)
print(f"\nAnchors with SED data: {len(spectral_db)}")
print(f"  2MASS (JHK):          {n_with_2mass}")
print(f"  WISE (W1-W4):         {n_with_wise}")
print(f"  Both bands:           {n_with_both}")

# Color distributions
colors_jh = [s["J-H"] for s in spectral_db if "J-H" in s]
colors_hk = [s["H-K"] for s in spectral_db if "H-K" in s]
colors_w12 = [s["W1-W2"] for s in spectral_db if "W1-W2" in s]
colors_w23 = [s["W2-W3"] for s in spectral_db if "W2-W3" in s]
alpha_jk = [s["alpha_JK"] for s in spectral_db if "alpha_JK" in s]
alpha_w12 = [s["alpha_W12"] for s in spectral_db if "alpha_W12" in s]

def stats(arr, name):
    if not arr:
        print(f"  {name}: no data")
        return
    arr.sort()
    n = len(arr)
    print(f"  {name:10s}: n={n:3d}  med={arr[n//2]:+.3f}  [{arr[n//4]:+.3f} ~ {arr[3*n//4]:+.3f}]")

print(f"\n--- Color Distributions ---")
stats(colors_jh, "J-H")
stats(colors_hk, "H-K")
stats(colors_w12, "W1-W2")
stats(colors_w23, "W2-W3")
print(f"\n--- Spectral Indices ---")
stats(alpha_jk, "alpha_JK")
stats(alpha_w12, "alpha_W12")

# SED types
print(f"\n--- SED Classification ---")
types = defaultdict(int)
for s in spectral_db:
    flags = s.get("flags", [])
    if "FULL_SED" in flags:
        types["Full SED (>=5 bands)"] += 1
    if "IR_EXCESS_WISE" in flags:
        types["WISE IR excess"] += 1
    if "STRONG_IR_EXCESS" in flags:
        types["Strong IR excess"] += 1
    if "RED_ANOMALY" in flags:
        types["Red color anomaly"] += 1
    if "BLUE_NIR" in flags:
        types["Blue NIR"] += 1
    if "BRIGHT" in flags:
        types["Bright (<10 mag)"] += 1
    if "MODERATE" in flags and "BRIGHT" not in flags:
        types["Moderate (10-14 mag)"] += 1

for t, c in sorted(types.items(), key=lambda x: -x[1]):
    print(f"  {t:25s}: {c}")

# Print sample SEDs
print(f"\n--- Sample SEDs (brightest anchors) ---")
brightest = sorted([s for s in spectral_db if "J" in s], key=lambda s: s.get("J", 99))[:8]
for s in brightest:
    bands = {k: s[k] for k in ("J","H","K","W1","W2","W3","W4") if k in s}
    flags = ",".join(s.get("flags", []))
    alpha = f" a_JK={s.get('alpha_JK','?')}" if "alpha_JK" in s else ""
    print(f"  {s['anchor']:20s} {bands}  |{alpha}  | {flags}")

# Save
with open(OUTPUT, "w") as f:
    json.dump(spectral_db, f, indent=2)
print(f"\nSaved: {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")

# Report
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("# BlackHole Beacon — Spectral Feature Database\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write("## Summary\n\n")
    f.write(f"- Anchors with SED data: {len(spectral_db)}\n")
    f.write(f"- 2MASS coverage: {n_with_2mass}\n")
    f.write(f"- WISE coverage: {n_with_wise}\n")
    f.write(f"- Both: {n_with_both}\n\n")
    f.write("## Color Statistics\n\n")
    f.write("| Color | n | Median | IQR |\n|-------|---|--------|-----|\n")
    for name, arr in [("J-H", colors_jh), ("H-K", colors_hk), ("W1-W2", colors_w12), ("W2-W3", colors_w23)]:
        if arr:
            arr.sort()
            f.write(f"| {name} | {len(arr)} | {arr[len(arr)//2]:.3f} | {arr[len(arr)//4]:.3f} ~ {arr[3*len(arr)//4]:.3f} |\n")
    f.write("\n## Spectral Indices\n\n")
    f.write("| Index | n | Median | IQR |\n|-------|---|--------|-----|\n")
    for name, arr in [("alpha_JK", alpha_jk), ("alpha_W12", alpha_w12)]:
        if arr:
            arr.sort()
            f.write(f"| {name} | {len(arr)} | {arr[len(arr)//2]:+.3f} | {arr[len(arr)//4]:+.3f} ~ {arr[3*len(arr)//4]:+.3f} |\n")
    f.write("\n## SED Types\n\n")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        f.write(f"- {t}: {c}\n")
    f.write("\n## Sample Brightest Anchors\n\n")
    f.write("| Anchor | Type | J | H | K | W1 | W2 | alpha_JK | Flags |\n")
    f.write("|--------|------|---|---|---|---|----------|--------|------|\n")
    for s in brightest:
        f.write(f"| {s['anchor']} | {s['type']} | {s.get('J','')} | {s.get('H','')} | {s.get('K','')} | {s.get('W1','')} | {s.get('W2','')} | {s.get('alpha_JK','')} | {','.join(s.get('flags',[]))} |\n")

print(f"Report: {REPORT}")
print("Done.")
