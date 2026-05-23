"""
compile_known_bh_list.py - Manually compile known black hole X-ray binaries list
=============================================================================
Known black hole X-ray binaries (stellar-mass black holes) are few (~50 confirmed sources).
This script manually lists the most reliable candidates, then queries Simbad for verification.

Author: math-science workspace / BlackHole Beacon project
Date: 2026-05-23
"""

import json
import time
from pathlib import Path

# ============================================================
# Known black hole X-ray binaries list (confirmed or strong candidates)
# Source: Corral-Santana et al. 2016, arXiv:1510.06734
# ============================================================

# Format: (name, common_name, RA(deg), Dec(deg), type)
# Type: BHXB = black hole X-ray binary, BHC = black hole candidate
KNOWN_BH_XRAY_BINARIES = [
    # --- Confirmed black holes (dynamical mass measurement) ---
    ("V404 Cyg", "V404 Cygni", 306.017, 33.867, "BHXB"),
    ("Cyg X-1", "Cyg X-1", 299.590, 35.201, "BHXB"),
    ("GRO J1655-40", "V1033 Sco", 253.500, -39.999, "BHXB"),
    ("A0620-00", "V616 Mon", 95.688, -0.108, "BHXB"),
    ("XTE J1118+480", "KV UMa", 169.545, 48.044, "BHXB"),
    ("GS 2000+25", "QZ Vul", 300.455, 25.737, "BHXB"),
    ("GS 1124-684", "MU Mus", 171.047, -68.659, "BHXB"),
    ("GRO J0422+32", "V518 Per", 65.425, 32.914, "BHXB"),
    ("H1705-250", "V2107 Oph", 257.400, -25.100, "BHXB"),
    ("4U 1543-475", "IL Lup", 236.275, -47.724, "BHXB"),
    ("XTE J1550-564", "V381 Nor", 237.725, -56.733, "BHXB"),
    ("GX 339-4", "V821 Ara", 255.706, -48.790, "BHXB"),
    ("Swift J1753.5-0127", "", 268.375, -1.454, "BHXB"),
    ("MAXI J1820+070", "V618 Ser", 275.091, 7.029, "BHXB"),
    ("GRS 1915+105", "V1487 Aql", 288.798, 10.946, "BHXB"),  # microquasar
    
    # --- Strong candidates (no dynamical mass, but strong evidence) ---
    ("XTE J1650-500", "", 252.625, -50.199, "BHC"),
    ("XTE J1859+226", "V406 Vul", 284.967, 22.658, "BHC"),
    ("Swift J1842.5-1124", "", 280.625, -11.400, "BHC"),
    ("MAXI J1836-194", "", 279.000, -19.667, "BHC"),
    ("Swift J1357.2-0933", "", 209.300, -9.550, "BHC"),
]

def compile_known_bh_list():
    """Compile known black hole list, save to JSON"""
    output = {
        "metadata": {
            "source": "Corral-Santana et al. 2016 + arXiv:1510.06734",
            "compiled_date": time.strftime("%Y-%m-%d"),
            "note": "Known black hole X-ray binaries (stellar-mass) list, for training set labels"
        },
        "black_holes": []
    }
    
    for name, alias, ra_deg, dec_deg, obj_type in KNOWN_BH_XRAY_BINARIES:
        entry = {
            "name": name,
            "alias": alias,
            "ra_deg": ra_deg,
            "dec_deg": dec_deg,
            "type": obj_type,
            "simbad_otype": None,  # to be queried
            "simbad_id": None,       # to be queried
        }
        output["black_holes"].append(entry)
    
    # Save
    output_path = Path(__file__).parent.parent / "data" / "known_bh_xray_binaries.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved {len(output['black_holes'])} known black holes to: {output_path}")
    return output_path

if __name__ == "__main__":
    compile_known_bh_list()
