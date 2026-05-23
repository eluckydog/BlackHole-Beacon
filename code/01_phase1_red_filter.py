"""BlackHole Beacon — Phase 1 Analysis Pipeline v1.0
Cross-match analysis: 2MASS + WISE color-magnitude diagrams,
population stats, and anomaly detection.
"""

import json, os, sys
from collections import Counter
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "data", "batch_all_results.json")
REPORT = os.path.join(ROOT, "data", "phase1_report_full.md")

with open(DATA_FILE) as f:
    data = json.load(f)

print(f"BlackHole Beacon — Phase 1 Analysis")
print(f"{'='*50}")

# ==============================
# 1. Anchor population stats
# ==============================
types = Counter(a["anchor"]["type"] for a in data)
print(f"\n--- Anchor Types ---")
for t, c in types.most_common():
    print(f"  {t:10s}: {c}")

# ==============================
# 2. Catalog coverage
# ==============================
both = sum(1 for d in data if "2mass" in d.get("matches",{}) and "wise" in d.get("matches",{}))
only_2m = sum(1 for d in data if "2mass" in d.get("matches",{}) and "wise" not in d.get("matches",{}))
only_w = sum(1 for d in data if "wise" in d.get("matches",{}) and "2mass" not in d.get("matches",{}))
print(f"\n--- Catalog Coverage ---")
print(f"  2MASS + WISE: {both}")
print(f"  Only 2MASS:   {only_2m}")
print(f"  Only WISE:    {only_w}")

# ==============================
# 3. Magnitude distributions
# ==============================
j_mags = []
h_mags = []
k_mags = []
w1_mags = []
w2_mags = []

for d in data:
    for m in d.get("matches",{}).get("2mass",[]):
        try:
            j = float(m.get("j_m",""))
            h = float(m.get("h_m",""))
            k = float(m.get("k_m",""))
            if 0 < j < 30: j_mags.append(j)
            if 0 < h < 30: h_mags.append(h)
            if 0 < k < 30: k_mags.append(k)
        except ValueError:
            pass
    for m in d.get("matches",{}).get("wise",[]):
        try:
            w1 = float(m.get("w1mpro",""))
            w2 = float(m.get("w2mpro",""))
            if 0 < w1 < 30: w1_mags.append(w1)
            if 0 < w2 < 30: w2_mags.append(w2)
        except ValueError:
            pass

def stats(arr, name):
    if not arr:
        return f"  {name:6s}: no data"
    arr.sort()
    n = len(arr)
    return f"  {name:6s}: n={n:4d}  min={arr[0]:5.2f}  p25={arr[n//4]:5.2f}  med={arr[n//2]:5.2f}  p75={arr[3*n//4]:5.2f}  max={arr[-1]:5.2f}"

print(f"\n--- Magnitude Statistics ---")
print(stats(j_mags, "J"))
print(stats(h_mags, "H"))
print(stats(k_mags, "K"))
print(stats(w1_mags, "W1"))
print(stats(w2_mags, "W2"))

# ==============================
# 4. Color-color distribution
# ==============================
colors_jh = []
colors_hk = []
colors_w1w2 = []
colors_w2w3 = []

for d in data:
    rows = d.get("matches",{}).get("2mass",[])
    # Take brightest source
    best = None
    best_j = 99
    for r in rows:
        try:
            j = float(r.get("j_m","99"))
            if j < best_j:
                best_j = j
                best = r
        except ValueError:
            pass
    if best:
        try:
            j = float(best.get("j_m",""))
            h = float(best.get("h_m",""))
            k = float(best.get("k_m",""))
            if all(0 < x < 30 for x in [j,h,k]):
                colors_jh.append(j - h)
                colors_hk.append(h - k)
        except ValueError:
            pass

    rows_w = d.get("matches",{}).get("wise",[])
    best_w = None
    best_w1 = 99
    for r in rows_w:
        try:
            w1 = float(r.get("w1mpro","99"))
            if w1 < best_w1:
                best_w1 = w1
                best_w = r
        except ValueError:
            pass
    if best_w:
        try:
            w1 = float(best_w.get("w1mpro",""))
            w2 = float(best_w.get("w2mpro",""))
            w3 = float(best_w.get("w3mpro",""))
            if all(0 < x < 30 for x in [w1,w2,w3]):
                colors_w1w2.append(w1 - w2)
                colors_w2w3.append(w2 - w3)
        except ValueError:
            pass

print(f"\n--- Color Statistics (brightest source per anchor) ---")
print(stats(colors_jh, "J-H"))
print(stats(colors_hk, "H-K"))
print(stats(colors_w1w2, "W1-W2"))
print(stats(colors_w2w3, "W2-W3"))

# ==============================
# 5. Anomaly candidates
# ==============================
print(f"\n--- Anomaly Candidates ---")
# Red objects (high J-H or H-K)
anomalies = []
for d in data:
    rows = d.get("matches",{}).get("2mass",[])
    for r in rows:
        try:
            j = float(r.get("j_m",""))
            h = float(r.get("h_m",""))
            k = float(r.get("k_m",""))
            if all(0 < x < 30 for x in [j,h,k]):
                jh = j - h
                hk = h - k
                if jh > 0.5 or hk > 0.5:  # 放宽阈值（原 1.0/0.8）
                    anomalies.append({
                        "anchor": d["anchor"]["name"],
                        "type": d["anchor"]["type"],
                        "src": r.get("designation",""),
                        "J-H": round(jh,2),
                        "H-K": round(hk,2),
                    })
        except ValueError:
            pass

print(f"  Red objects (J-H>1.0 or H-K>0.8): {len(anomalies)}")
for a in anomalies[:10]:
    print(f"    {a['anchor']:20s} ({a['type']:6s})  src={a['src']:18s}  J-H={a['J-H']:5.2f}  H-K={a['H-K']:5.2f}")
if len(anomalies) > 10:
    print(f"    ... and {len(anomalies)-10} more")

# ==============================
# 6. Best detections (brightest)
# ==============================
print(f"\n--- Brightest Detections ---")
all_sources = []
for d in data:
    for r in d.get("matches",{}).get("2mass",[]):
        try:
            j = float(r.get("j_m","99"))
            if j < 20:
                all_sources.append((j, "2MASS", d["anchor"]["name"], d["anchor"]["type"], r.get("designation","")))
        except ValueError:
            pass
    for r in d.get("matches",{}).get("wise",[]):
        try:
            w1 = float(r.get("w1mpro","99"))
            if w1 < 20:
                all_sources.append((w1, "WISE", d["anchor"]["name"], d["anchor"]["type"], r.get("designation","")))
        except ValueError:
            pass

all_sources.sort(key=lambda x: x[0])
for j, cat, name, atype, desig in all_sources[:15]:
    print(f"  {cat:5s} {j:5.2f} mag  | {name:20s} ({atype:6s})  {desig:20s}")

# ==============================
# 7. Summary report
# ==============================
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(f"# BlackHole Beacon — Phase 1 Analysis Report\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"## Overview\n\n")
    f.write(f"- **Total anchors with data:** {len(data)}\n")
    f.write(f"- **Total IR sources detected:** {len(j_mags) + len(w1_mags)}\n")
    f.write(f"- **2MASS sources:** {len(j_mags)}\n")
    f.write(f"- **WISE sources:** {len(w1_mags)}\n\n")
    f.write(f"## Anchor Breakdown\n\n")
    f.write(f"| Type | Count |\n|------|-------|\n")
    for t, c in types.most_common():
        f.write(f"| {t} | {c} |\n")
    f.write(f"\n## Coverage\n\n")
    f.write(f"- Both 2MASS + WISE: {both}\n")
    f.write(f"- 2MASS only: {only_2m}\n")
    f.write(f"- WISE only: {only_w}\n\n")
    f.write(f"## Color Statistics\n\n")
    f.write(f"| Color | n | Median | Range |\n|-------|---|--------|-------|\n")
    if colors_jh:
        f.write(f"| J-H | {len(colors_jh)} | {sorted(colors_jh)[len(colors_jh)//2]:.2f} | {min(colors_jh):.2f} ~ {max(colors_jh):.2f} |\n")
    if colors_hk:
        f.write(f"| H-K | {len(colors_hk)} | {sorted(colors_hk)[len(colors_hk)//2]:.2f} | {min(colors_hk):.2f} ~ {max(colors_hk):.2f} |\n")
    if colors_w1w2:
        f.write(f"| W1-W2 | {len(colors_w1w2)} | {sorted(colors_w1w2)[len(colors_w1w2)//2]:.2f} | {min(colors_w1w2):.2f} ~ {max(colors_w1w2):.2f} |\n")
    if colors_w2w3:
        f.write(f"| W2-W3 | {len(colors_w2w3)} | {sorted(colors_w2w3)[len(colors_w2w3)//2]:.2f} | {min(colors_w2w3):.2f} ~ {max(colors_w2w3):.2f} |\n")
    f.write(f"\n## Anomalies\n\n")
    f.write(f"- Red objects (J-H>1.0 or H-K>0.8): {len(anomalies)}\n\n")
    f.write(f"## Brightest Sources\n\n")
    f.write(f"| Catalog | Mag | Anchor | Type | Designation |\n|---------|-----|--------|------|-------------|\n")
    for j, cat, name, atype, desig in all_sources[:10]:
        f.write(f"| {cat} | {j:.2f} | {name} | {atype} | {desig} |\n")

print(f"\n{'='*50}")
print(f"Report saved: {REPORT}")
print(f"Done.")
