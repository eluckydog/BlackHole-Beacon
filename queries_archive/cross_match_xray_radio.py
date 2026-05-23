"""
Cross-match TOP 10 anomalies with X-ray/radio catalogs.

WHY? Pulsars/BH are X-ray/radio sources.
If a TOP 10 anomaly has X-ray/radio counterpart -> high priority candidate.

Steps:
1. Fermi 4FGL (γ-ray) - pulsars are γ-ray sources
2. ROSAT (X-ray) - pulsars/BH are X-ray sources
3. NVSS (radio) - pulsars are radio sources
"""

import json
import os
import numpy as np
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

print("BlackHole Beacon — Cross-Match with X-ray/Radio Catalogs")
print("="*80)

# ==========
# 1. Load v8.0 TOP 10
# ==========
print("\n--- 1. Load v8.0 TOP 10 ---")

ranking_file = os.path.join(DATA_DIR, "classifier_ranking_v8.json")
with open(ranking_file, "r") as f:
    ranking = json.load(f)

top10 = ranking[:10]

print(f"  TOP 10 anomalies (v8.0):")
for i, r in enumerate(top10):
    print(f"    {i+1}. {r['anchor']} (prob={r['prob']:.4f})")

# ==========
# 2. Load candidate details (RA/DEC)
# ==========
print("\n--- 2. Load Candidate Details (RA/DEC) ---")

phase3_file = os.path.join(DATA_DIR, "phase3_candidates_full.json")
with open(phase3_file, "r") as f:
    candidates = json.load(f)

# Build anchor -> candidate mapping
candidate_dict = {c.get("anchor", f"UNK_{i}"): c for i, c in enumerate(candidates)}

# Get RA/DEC for TOP 10
top10_details = []
for r in top10:
    anchor = r["anchor"]
    if anchor in candidate_dict:
        c = candidate_dict[anchor]
        ra = c.get("ra", 0.0) or 0.0
        dec = c.get("dec", 0.0) or 0.0
        top10_details.append({
            "anchor": anchor,
            "ra": ra,
            "dec": dec,
            "prob": r["prob"]
        })
    else:
        print(f"  WARNING: {anchor} not found in phase3_candidates_full.json")

print(f"  Loaded RA/DEC for {len(top10_details)} / 10 anomalies")

# ==========
# 3. Cross-match with Fermi 4FGL (γ-ray)
# ==========
print("\n--- 3. Cross-Match with Fermi 4FGL (γ-ray) ---")

# Fermi 4FGL catalog (Vizier)
# This is a LARGE catalog (~7000 sources)
# We'll use a LOCAL copy (if available) or query Vizier (if online)

fermi_file = os.path.join(DATA_DIR, "fermi_4fgl.json")

if os.path.exists(fermi_file):
    print("  Loading LOCAL Fermi 4FGL catalog...")
    with open(fermi_file, "r") as f:
        fermi_sources = json.load(f)
    print(f"  Loaded {len(fermi_sources)} Fermi sources")
else:
    print("  Fermi 4FGL catalog NOT FOUND locally.")
    print("  Attempting to query Vizier (Fermi 4FGL)...")
    
    try:
        # Query Vizier for Fermi 4FGL
        # Catalog: J/ApJS/247/33 (4FGL-DR4)
        v = Vizier(
            columns=['4FGL', 'RAJ2000', 'DEJ2000', 'Sig_Curve'],
            row_limit=-1
        )
        result = v.get_catalogs('J/ApJS/247/33')
        
        if len(result) > 0:
            fermi_sources = []
            for row in result[0]:
                fermi_sources.append({
                    "4FGL": row['4FGL'],
                    "ra": row['RAJ2000'],
                    "dec": row['DEJ2000'],
                    "sig_curve": row['Sig_Curve']
                })
            
            # Save locally
            with open(fermi_file, "w") as f:
                json.dump(fermi_sources, f, indent=2)
            
            print(f"  Downloaded and saved {len(fermi_sources)} Fermi sources")
        else:
            print("  WARNING: No results from Vizier")
            fermi_sources = []
    
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  Skipping Fermi cross-match")
        fermi_sources = []

# Cross-match TOP 10 with Fermi
print(f"\n  Cross-matching TOP 10 with Fermi 4FGL...")
fermi_matches = []

for det in top10_details:
    anchor = det["anchor"]
    ra = det["ra"]
    dec = det["dec"]
    
    # Simple positional cross-match (within 10 arcsec)
    match = None
    min_sep = 10.0  # arcsec
    
    for src in fermi_sources:
        sep = np.sqrt((ra - src["ra"])**2 + (dec - src["dec"])**2) * 3600.0  # to arcsec
        if sep < min_sep:
            min_sep = sep
            match = src
    
    if match:
        fermi_matches.append({
            "anchor": anchor,
            "fermi_id": match["4FGL"],
            "sep_arcsec": min_sep,
            "sig_curve": match["sig_curve"]
        })
        print(f"    {anchor} -> {match['4FGL']} (sep={min_sep:.1f}\")")

print(f"  Fermi matches: {len(fermi_matches)} / 10")

# ==========
# 4. Cross-match with ROSAT (X-ray)
# ==========
print("\n--- 4. Cross-Match with ROSAT (X-ray) ---")

rosat_file = os.path.join(DATA_DIR, "rosat_xray.json")

if os.path.exists(rosat_file):
    print("  Loading LOCAL ROSAT catalog...")
    with open(rosat_file, "r") as f:
        rosat_sources = json.load(f)
    print(f"  Loaded {len(rosat_sources)} ROSAT sources")
else:
    print("  ROSAT catalog NOT FOUND locally.")
    print("  Attempting to query Vizier (ROSAT)...")
    
    try:
        # Query Vizier for ROSAT (1RXS)
        # Catalog: J/A+A/588/A10 (1RXS)
        v = Vizier(
            columns=['1RXS', 'RAJ2000', 'DEJ2000', 'CountRate'],
            row_limit=-1
        )
        result = v.get_catalogs('J/A+A/588/A10')
        
        if len(result) > 0:
            rosat_sources = []
            for row in result[0]:
                rosat_sources.append({
                    "1RXS": row['1RXS'],
                    "ra": row['RAJ2000'],
                    "dec": row['DEJ2000'],
                    "count_rate": row['CountRate']
                })
            
            # Save locally
            with open(rosat_file, "w") as f:
                json.dump(rosat_sources, f, indent=2)
            
            print(f"  Downloaded and saved {len(rosat_sources)} ROSAT sources")
        else:
            print("  WARNING: No results from Vizier")
            rosat_sources = []
    
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  Skipping ROSAT cross-match")
        rosat_sources = []

# Cross-match TOP 10 with ROSAT
print(f"\n  Cross-matching TOP 10 with ROSAT...")
rosat_matches = []

for det in top10_details:
    anchor = det["anchor"]
    ra = det["ra"]
    dec = det["dec"]
    
    # Simple positional cross-match (within 30 arcsec, X-ray pos uncertain)
    match = None
    min_sep = 30.0  # arcsec
    
    for src in rosat_sources:
        sep = np.sqrt((ra - src["ra"])**2 + (dec - src["dec"])**2) * 3600.0  # to arcsec
        if sep < min_sep:
            min_sep = sep
            match = src
    
    if match:
        rosat_matches.append({
            "anchor": anchor,
            "rosat_id": match["1RXS"],
            "sep_arcsec": min_sep,
            "count_rate": match["count_rate"]
        })
        print(f"    {anchor} -> {match['1RXS']} (sep={min_sep:.1f}\")")

print(f"  ROSAT matches: {len(rosat_matches)} / 10")

# ==========
# 5. Skip NVSS (radio) - Vizier connection unstable
# ==========
print("\n--- 5. Skip NVSS (radio) ---")
print("  Skipping NVSS query (Vizier connection unstable).")
nvss_matches = []

# ==========
# 6. Summary
# ==========
print("\n" + "="*80)
print("SUMMARY:")
print("="*80)

print(f"\n  TOP 10 Anomalies (v8.0) Cross-Match Results:")
print(f"    Fermi 4FGL (γ-ray): {len(fermi_matches)} / 10")
print(f"    ROSAT (X-ray):      {len(rosat_matches)} / 10")
print(f"    NVSS (radio):       {len(nvss_matches)} / 10")

print(f"\n  HIGH PRIORITY Candidates (any X-ray/radio match):")
high_priority = set()
for m in fermi_matches:
    high_priority.add(m["anchor"])
for m in rosat_matches:
    high_priority.add(m["anchor"])
for m in nvss_matches:
    high_priority.add(m["anchor"])

if len(high_priority) > 0:
    for anchor in high_priority:
        print(f"    {anchor}")
        # Check which catalogs matched
        fermi_match = next((m for m in fermi_matches if m["anchor"] == anchor), None)
        rosat_match = next((m for m in rosat_matches if m["anchor"] == anchor), None)
        nvss_match = next((m for m in nvss_matches if m["anchor"] == anchor), None)
        
        if fermi_match:
            print(f"      Fermi: {fermi_match['fermi_id']} (sep={fermi_match['sep_arcsec']:.1f}\")")
        if rosat_match:
            print(f"      ROSAT: {rosat_match['rosat_id']} (sep={rosat_match['sep_arcsec']:.1f}\")")
        if nvss_match:
            print(f"      NVSS: {nvss_match['nvss_id']} (sep={nvss_match['sep_arcsec']:.1f}\")")
else:
    print("    NONE")
    print("\n  Possible reasons:")
    print("    1. TOP 10 are false positives (AGN, YSO, etc.)")
    print("    2. X-ray/radio counterparts are too faint to be detected")
    print("    3. Our positional cross-match radius is too small")

print("\n" + "="*80)
print("NEXT STEPS:")
print("="*80)

print("""
  1. If HIGH PRIORITY candidates exist:
     -> Follow-up with targeted observations (deeper IR, X-ray, radio)
  
  2. If NO matches:
     -> Check IR images (2MASS/WISE) for TOP 10
     -> If IR morphology looks like galaxy -> likely AGN
     -> If IR morphology looks like point source -> could be pulsar/BH
  
  3. Adjust Isolation Forest parameters (contamination)
     -> If too many false positives (contamination too high)
     -> If too few candidates (contamination too low)
""")

print("="*80)
print("DONE. Cross-match complete.")
print("="*80)
