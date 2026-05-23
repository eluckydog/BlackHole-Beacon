"""BlackHole Beacon — Color-Color Diagram Generator v1.0"""

import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "data", "batch_all_results.json")
OUT_DIR = os.path.join(ROOT, "data", "plots")
os.makedirs(OUT_DIR, exist_ok=True)
REPORT = os.path.join(ROOT, "data", "color_color_report.md")

with open(DATA_FILE) as f:
    data = json.load(f)

print("BlackHole Beacon — Color-Color Diagrams")
print("=" * 50)

# ── 1. Collect data ──────────────────────────────────────────────
jh_hk = []   # (J-H, H-K, anchor, source_id)
w12_w23 = []  # (W1-W2, W2-W3 or None, anchor, source_id)

for anchor in data:
    a_name = anchor["anchor"]["name"]
    matches = anchor.get("matches", {})

    for m in matches.get("2mass", []):
        try:
            j = float(m.get("j_m", ""))
            h = float(m.get("h_m", ""))
            k = float(m.get("k_m", ""))
            if -1 < j < 30 and -1 < h < 30 and -1 < k < 30:
                jh_hk.append((j - h, h - k, a_name, m.get("designation", "")))
        except (ValueError, TypeError):
            pass

    for m in matches.get("wise", []):
        try:
            w1 = float(m.get("w1mpro", ""))
            w2 = float(m.get("w2mpro", ""))
            w3 = m.get("w3mpro")
            w3v = float(w3) if w3 else None
            if -1 < w1 < 30 and -1 < w2 < 30:
                w12 = w1 - w2
                w23 = (w2 - w3v) if (w3v is not None and -1 < w3v < 30) else None
                w12_w23.append((w12, w23, a_name, m.get("designation", "")))
        except (ValueError, TypeError):
            pass

print(f"\n--- Data ---")
print(f"  J-H vs H-K  : {len(jh_hk)} points")
print(f"  W1-W2 vs W2-W3: {len(w12_w23)} points")

# ── 2. 3-sigma outliers ───────────────────────────────────────────
def find_outliers(values, paired, threshold=3.0):
    """values = list of floats, paired = list of (v, jh, hk, a, s)
       returns [(jh, hk, a, s), ...]"""
    arr = np.array(values)
    mu = float(np.mean(arr))
    sig = float(np.std(arr))
    out = []
    for v, jh, hk, a, s in paired:
        if abs(v - mu) > threshold * sig:
            out.append((jh, hk, a, s))
    return out, (mu, sig)

jh_vals = [v for v, _, _, _, _ in [(jh, jh, hk, a, s)
                                       for jh, hk, a, s in jh_hk]]
jh_paired = [(jh, jh, hk, a, s) for jh, hk, a, s in jh_hk]
jh_out, (jh_mu, jh_sig) = find_outliers(jh_vals, jh_paired)

hk_vals = [v for v, _, _, _, _ in [(hk, jh, hk, a, s)
                                       for jh, hk, a, s in jh_hk]]
hk_paired = [(hk, jh, hk, a, s) for jh, hk, a, s in jh_hk]
hk_out, (hk_mu, hk_sig) = find_outliers(hk_vals, hk_paired)

all_out_anchors = set(a for _, _, a, _ in jh_out + hk_out)
print(f"\n--- 3σ Outliers ---")
print(f"  J-H outliers : {len(jh_out)}  (μ={jh_mu:.3f}, σ={jh_sig:.3f})")
print(f"  H-K outliers : {len(hk_out)}  (μ={hk_mu:.3f}, σ={hk_sig:.3f})")
print(f"  Affected anchors: {len(all_out_anchors)}")

# ── 3. Plot ────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("BlackHole Beacon — Color-Color Diagrams", fontsize=14)

# Panel 1: J-H vs H-K
ax = axes[0]
jhs = [jh for jh, _, _, _ in jh_hk]
hks = [hk for _, hk, _, _ in jh_hk]
ax.scatter(jhs, hks, s=8, alpha=0.4, c="steelblue", edgecolors="none")
ax.set_xlabel("J-H (mag)", fontsize=12)
ax.set_ylabel("H-K (mag)", fontsize=12)
ax.set_title(f"2MASS: J-H vs H-K  (n={len(jh_hk)})", fontsize=11)
ax.grid(True, alpha=0.3)
ax.axvline(x=jh_mu, color="red", ls="--", alpha=0.5,
           label=f"J-H μ={jh_mu:.2f}")
ax.axhline(y=hk_mu, color="red", ls="--", alpha=0.5,
           label=f"H-K μ={hk_mu:.2f}")
# mark outliers
for jh, hk, a, s in jh_out + hk_out:
    ax.scatter([jh], [hk], s=25, c="red", marker="x", zorder=10)
ax.legend(fontsize=8)

# Panel 2: W1-W2 vs W2-W3
ax = axes[1]
w12_p, w23_p, jw_p, hw_p = [], [], [], []
for w12, w23, a, s in w12_w23:
    if w23 is not None:
        w12_p.append(w12)
        w23_p.append(w23)
        jw_p.append(a)
        hw_p.append(s)

if w12_p:
    w12_mu = float(np.mean(w12_p))
    w23_mu = float(np.mean(w23_p))
    ax.scatter(w12_p, w23_p, s=8, alpha=0.4, c="darkgreen", edgecolors="none")
    ax.set_xlabel("W1-W2 (mag)", fontsize=12)
    ax.set_ylabel("W2-W3 (mag)", fontsize=12)
    ax.set_title(f"WISE: W1-W2 vs W2-W3  (n={len(w12_p)})", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.axvline(x=w12_mu, color="red", ls="--", alpha=0.5,
               label=f"W1-W2 μ={w12_mu:.2f}")
    ax.axhline(y=w23_mu, color="red", ls="--", alpha=0.5,
               label=f"W2-W3 μ={w23_mu:.2f}")
    ax.legend(fontsize=8)
else:
    ax.text(0.5, 0.5, "No W3 data", ha="center", va="center",
            transform=ax.transAxes, fontsize=12)
    ax.set_title("WISE: W1-W2 vs W2-W3  (no W3 data)", fontsize=11)

plt.tight_layout()
out_png = os.path.join(OUT_DIR, "color_color_diagrams.png")
plt.savefig(out_png, dpi=150, bbox_inches="tight")
print(f"\nSaved: {out_png}")

# ── 4. Report ──────────────────────────────────────────────────────
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("# Color-Color Diagram Report\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

    f.write("## J-H vs H-K\n\n")
    f.write(f"- Total points: {len(jh_hk)}\n")
    f.write(f"- J-H  μ={jh_mu:.3f}, σ={jh_sig:.3f}\n")
    f.write(f"- H-K  μ={hk_mu:.3f}, σ={hk_sig:.3f}\n")
    f.write(f"- 3σ outliers: {len(set(a for _,_,a,_ in jh_out+hk_out))} anchors\n\n")

    f.write("## W1-W2 vs W2-W3\n\n")
    if w12_p:
        w12_std = float(np.std(w12_p))
        w23_std = float(np.std(w23_p))
        f.write(f"- Paired points: {len(w12_p)}\n")
        f.write(f"- W1-W2  μ={np.mean(w12_p):.3f}, σ={w12_std:.3f}\n")
        f.write(f"- W2-W3  μ={np.mean(w23_p):.3f}, σ={w23_std:.3f}\n\n")
    else:
        f.write("- No paired W2-W3 data available\n\n")

    f.write("## Interpretation\n\n")
    f.write("- **J-H > 1.0, H-K > 0.8**: Likely AGB star / carbon star / dusty\n")
    f.write("- **J-H < 0, H-K < 0**: Blue excess (possible pulsar contribution)\n")
    f.write("- **W1-W2 > 0.5**: IR excess (circumstellar dust / PWNe)\n")
    f.write("- **W1-W2 < -0.5**: IR deficit (unusual)\n\n")

    f.write("## Outlier Anchors (3σ)\n\n")
    out_counts = {}
    for _, _, a, _ in jh_out + hk_out:
        out_counts[a] = out_counts.get(a, 0) + 1
    for a, c in sorted(out_counts.items(), key=lambda x: -x[1])[:20]:
        f.write(f"- **{a}**: {c} outlier(s)\n")

print(f"Report: {REPORT}")
print("Done.")
