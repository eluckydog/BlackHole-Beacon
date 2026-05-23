"""BlackHole Beacon — SED Component Decomposer v1.0

Decomposes each anchor's multi-band SED into physical components:
  - Blackbody (stellar photosphere, temperature T)
  - Power-law (non-thermal emission, spectral index alpha)
  - Dust emission (MIR excess, temperature T_dust)

Outputs component fractions for each anchor, enabling population-level
analysis of what physical processes dominate each source's SED.
"""

import json, os, math
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES_FILE = os.path.join(ROOT, "data", "spectral_features.json")
OUTPUT = os.path.join(ROOT, "data", "sed_components.json")
REPORT = os.path.join(ROOT, "data", "sed_components_report.md")

with open(FEATURES_FILE) as f:
    spectral_db = json.load(f)

# ==============================
# Physical model: f_nu = A * BB(T) + B * nu^alpha + C * BB(T_dust)
# ==============================

def planck_nu(nu, T):
    """Blackbody flux density: B_nu(T) in Jy/sr.
    Returns relative values (normalized)."""
    h = 6.626e-27
    k = 1.381e-16
    c = 2.998e10
    if T <= 0:
        return 0
    x = h * nu / (k * T)
    if x > 100:  # Prevent underflow
        return 0
    return (2 * h * nu**3 / c**2) / (math.exp(x) - 1)

def nu_from_lambda_micron(lam):
    """Frequency in Hz from wavelength in microns."""
    return 2.998e14 / (lam * 1e-6)

# Wavelengths of our bands (microns) and approximate pivot points
BANDS_ORDERED = [
    ("J", 1.235), ("H", 1.662), ("K", 2.159),
    ("W1", 3.368), ("W2", 4.618), ("W3", 12.082), ("W4", 22.194),
]
BAND_NAMES = [b[0] for b in BANDS_ORDERED]

def component_analysis(sed):
    """Analyze a single SED and estimate component contributions.
    
    Returns:
        bb_frac: fraction of J-band flux from stellar blackbody
        pl_frac: fraction from non-thermal power-law
        dust_frac: fraction from dust emission
        bb_T: estimated blackbody temperature (K)
        alpha: power-law index
        dust_T: estimated dust temperature (K)
        fit_quality: how well the model fits (0-1)
    """
    # Collect available measurements
    wavelengths = []
    fluxes = []
    for name, lam in BANDS_ORDERED:
        mag = sed.get(name)
        if mag is not None and 0 < mag < 30:
            wavelengths.append(lam)
            # Convert mag to relative flux (Jy)
            zp = {"J": 1594, "H": 1024, "K": 667,
                  "W1": 309.54, "W2": 171.79, "W3": 31.67, "W4": 8.36}
            f = zp.get(name, 1000) * 10 ** (-mag / 2.5)
            fluxes.append(f)
    
    if len(wavelengths) < 3:
        return None  # Need at least 3 bands
    
    # Estimate stellar temperature from J-H color
    jh = sed.get("J-H")
    if jh is not None:
        # Rough empirical: hotter = bluer
        # For main sequence: J-H ~ 0.3 -> 6000K, J-H ~ 0.7 -> 4000K
        bb_T_guess = 6000 - (jh - 0.3) * 5000
        bb_T_guess = max(3000, min(30000, bb_T_guess))
    else:
        bb_T_guess = 5000
    
    # Estimate power-law index from JHK slope
    alpha_guess = sed.get("alpha_JK", 0.5)
    
    # Estimate dust component from W1-W2
    w12 = sed.get("W1-W2")
    if w12 is not None and w12 > 0.2:
        # W1-W2 > 0.2 suggests hot dust
        dust_T_guess = 800
    else:
        dust_T_guess = 0  # No dust
    
    # Compute model fluxes at each wavelength
    # Simple grid search for best component fractions
    bb = planck_nu(nu_from_lambda_micron(wavelengths[0]), bb_T_guess)
    pl = wavelengths[0] ** (-alpha_guess - 2)  # approximate f_nu ~ nu^alpha ~ lam^(-alpha-2)
    dust = planck_nu(nu_from_lambda_micron(wavelengths[0]), dust_T_guess) if dust_T_guess > 0 else 0
    
    # Normalize to J-band
    total_obs = fluxes[0]
    
    # Try different fractions via simple fit
    best_r = 0
    best_bb = 0.5
    best_pl = 0.3
    best_dust = 0.2
    best_t = bb_T_guess
    best_alpha = alpha_guess
    best_dt = dust_T_guess
    
    # Coarse grid search on temperatures
    for test_t in [3500, 5000, 7000, 10000, 15000, 25000]:
        for test_alpha in [-1.0, -0.5, 0.0, 0.5, 1.0, 2.0]:
            for test_dt in [0, 300, 500, 800, 1200]:
                bb_norm = [planck_nu(nu_from_lambda_micron(l), test_t) for l in wavelengths]
                pl_norm = [l ** (-test_alpha - 2) for l in wavelengths]
                dust_norm = [planck_nu(nu_from_lambda_micron(l), test_dt) for l in wavelengths] if test_dt > 0 else [0]*len(wavelengths)
                
                # Normalize so total = observed J-band
                A = bb_norm[0]
                B = pl_norm[0]
                C = dust_norm[0]
                denom = A + B + C
                if denom == 0:
                    continue
                
                # Fit fractions via linear least squares (approximate)
                # For each wavelength: obs = A*bb_frac + B*pl_frac + C*dust_frac
                # Simple: try 3 fractions, pick best
                for bb_frac in [0.2, 0.5, 0.8]:
                    for pl_frac in [0.0, 0.2, 0.5]:
                        for dust_frac in [0.0, 0.2, 0.5]:
                            total = bb_frac + pl_frac + dust_frac
                            if abs(total - 1.0) > 0.01:
                                continue
                            
                            model_fluxes = []
                            for i in range(len(wavelengths)):
                                m = (bb_frac * bb_norm[i] +
                                     pl_frac * pl_norm[i] +
                                     dust_frac * dust_norm[i])
                                model_fluxes.append(m)
                            
                            # Correlation between model and observed
                            obs_norm = [f / total_obs for f in fluxes]
                            model_norm = [m / model_fluxes[0] if model_fluxes[0] else 0 for m in model_fluxes]
                            
                            # Simple R: product of ratios
                            r = 0
                            for i in range(len(wavelengths)):
                                if obs_norm[i] > 0 and model_norm[i] > 0:
                                    ratio = min(obs_norm[i], model_norm[i]) / max(obs_norm[i], model_norm[i])
                                    r += ratio
                            r /= len(wavelengths)
                            
                            if r > best_r:
                                best_r = r
                                best_bb = bb_frac
                                best_pl = pl_frac
                                best_dust = dust_frac
                                best_t = test_t
                                best_alpha = test_alpha
                                best_dt = test_dt
    
    return {
        "bb_frac": round(best_bb, 3),
        "pl_frac": round(best_pl, 3),
        "dust_frac": round(best_dust, 3),
        "bb_T_K": best_t,
        "alpha": round(best_alpha, 1),
        "dust_T_K": best_dt,
        "fit_quality": round(best_r, 2),
        "n_bands": len(wavelengths),
    }

# ==============================
# Run decomposition
# ==============================

print("BlackHole Beacon — SED Component Decomposer")
print("=" * 55)

decomposed = []
bb_dominated = 0
pl_dominated = 0
dust_detected = 0
n_total = 0

for s in spectral_db:
    comp = component_analysis(s)
    if comp is None:
        continue
    n_total += 1
    
    entry = {
        "anchor": s["anchor"],
        "type": s["type"],
        "components": comp,
    }
    
    # Classify by dominant component
    if comp["dust_frac"] > 0.4:
        entry["class"] = "DUST_DOMINATED"
        dust_detected += 1
    elif comp["pl_frac"] > 0.5:
        entry["class"] = "PL_DOMINATED"
        pl_dominated += 1
    else:
        entry["class"] = "BB_DOMINATED"
        bb_dominated += 1
    
    decomposed.append(entry)

# Summary
print(f"\nSEDs analyzed: {n_total}")
print(f"\n--- Component Classification ---")
print(f"  Blackbody-dominated (star-like):  {bb_dominated} ({bb_dominated/n_total*100:.0f}%)")
print(f"  Power-law dominated (non-thermal): {pl_dominated} ({pl_dominated/n_total*100:.0f}%)")
print(f"  Dust emission detected:            {dust_detected} ({dust_detected/n_total*100:.0f}%)")

# Temperature distribution
temps_bb = [d["components"]["bb_T_K"] for d in decomposed if d["components"]["bb_T_K"] > 0]
temps_dust = [d["components"]["dust_T_K"] for d in decomposed if d["components"]["dust_T_K"] > 0]

if temps_bb:
    temps_bb.sort()
    print(f"\nBB temperatures: n={len(temps_bb)}, med={temps_bb[len(temps_bb)//2]}K, "
          f"[{min(temps_bb)}K ~ {max(temps_bb)}K]")

if temps_dust:
    temps_dust.sort()
    print(f"Dust temperatures: n={len(temps_dust)}, med={temps_dust[len(temps_dust)//2]}K, "
          f"[{min(temps_dust)}K ~ {max(temps_dust)}K]")

# Show sample decomposed SEDs
print(f"\n--- Sample Decompositions ---")
for d in decomposed[:10]:
    c = d["components"]
    print(f"  {d['anchor']:20s} {d['class']:18s} | BB={c['bb_frac']:.0%} PL={c['pl_frac']:.0%} Dust={c['dust_frac']:.0%} "
          f"| T={c['bb_T_K']}K alpha={c['alpha']:.1f} dust_T={c['dust_T_K']}K | fit={c['fit_quality']:.2f}")

# List dust-dominated sources
print(f"\n--- Dust-Dominated Sources ---")
for d in decomposed:
    if d["class"] == "DUST_DOMINATED":
        c = d["components"]
        print(f"  {d['anchor']:20s} ({d['type']:6s}) | BB={c['bb_frac']:.0%} PL={c['pl_frac']:.0%} Dust={c['dust_frac']:.0%} T_dust={c['dust_T_K']}K")

# List power-law dominated
print(f"\n--- Power-Law Dominated Sources ---")
for d in decomposed:
    if d["class"] == "PL_DOMINATED":
        c = d["components"]
        print(f"  {d['anchor']:20s} ({d['type']:6s}) alpha={c['alpha']:.1f} PL={c['pl_frac']:.0%}")

# Save
with open(OUTPUT, "w") as f:
    json.dump(decomposed, f, indent=2)
print(f"\nSaved: {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")

# Report
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("# BlackHole Beacon — SED Component Analysis\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write("## Physical Decomposition\n\n")
    f.write("Each anchor's SED is modeled as:\n\n")
    f.write("$$f_\\nu = A \\cdot B_\\nu(T_*) + B \\cdot \\nu^\\alpha + C \\cdot B_\\nu(T_d)$$\n\n")
    f.write("- **Blackbody** (stellar photosphere): temperature T*\n")
    f.write("- **Power-law** (non-thermal synchrotron): spectral index α\n")
    f.write("- **Dust emission** (circumstellar/environment): temperature T_d\n\n")
    f.write("## Population Summary\n\n")
    f.write(f"- Total SEDs: {n_total}\n")
    f.write(f"- BB-dominated: {bb_dominated} ({bb_dominated/n_total*100:.0f}%)\n")
    f.write(f"- PL-dominated: {pl_dominated} ({pl_dominated/n_total*100:.0f}%)\n")
    f.write(f"- Dust detected: {dust_detected} ({dust_detected/n_total*100:.0f}%)\n\n")
    f.write("## Dust Sources\n\n")
    for d in decomposed:
        if d["class"] == "DUST_DOMINATED":
            c = d["components"]
            f.write(f"- {d['anchor']} ({d['type']}): dust={c['dust_frac']:.0%}, T_dust={c['dust_T_K']}K\n")

print(f"Report: {REPORT}")
print("Done.")
