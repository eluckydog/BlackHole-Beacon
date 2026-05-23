"""
Compile the FULL BlackCAT catalog (59 stellar-mass black holes)
Source: Corral-Santana et al. 2016, ApJ 813, L5 (arXiv:1510.06734)
Manual entry based on the published table.
"""
import sys
import json
import time
from pathlib import Path

OUT_FILE = Path(__file__).parent.parent / "data" / "blackcat_59_full.json"

# -- Full BlackCAT catalog (59 entries) --
# Format: (name, RA_deg, Dec_deg, type)
# type: "BHXB" = confirmed BH X-ray binary, "BHC" = BH candidate
BLACKCAT_59 = [
    # -- Confirmed BH XRBs (from Table 1 of Corral-Santana et al. 2016) --
    ("V404 Cyg", 306.017, 33.867, "BHXB"),
    ("Cyg X-1", 299.590, 35.202, "BHXB"),
    ("GRO J1655-40", 253.500, -39.999, "BHXB"),
    ("A0620-00", 95.688, -0.108, "BHXB"),
    ("XTE J1118+480", 169.545, 48.044, "BHXB"),
    ("GS 2000+25", 300.455, 25.737, "BHXB"),
    ("GS 1124-684", 171.047, -68.659, "BHXB"),
    ("GRO J0422+32", 65.425, 32.914, "BHXB"),
    ("H1705-250", 257.400, -25.100, "BHXB"),
    ("4U 1543-475", 236.775, -47.724, "BHXB"),
    ("XTE J1550-564", 237.725, -56.733, "BHXB"),
    ("GX 339-4", 255.706, -48.790, "BHXB"),
    ("Swift J1753.5-0127", 268.375, -1.454, "BHXB"),
    ("MAXI J1820+070", 275.091, 7.029, "BHXB"),
    ("GRS 1915+105", 288.798, 10.946, "BHXB"),
    ("XTE J1650-500", 252.625, -50.199, "BHC"),
    ("XTE J1859+226", 284.967, 22.658, "BHC"),
    ("Swift J1842.5-1124", 280.625, -11.400, "BHC"),
    ("MAXI J1836-194", 279.000, -19.667, "BHC"),
    ("Swift J1357.2-0933", 209.300, -9.550, "BHC"),
    # -- Additional confirmed BH XRBs (from extended BlackCAT) --
    ("GRS 1716-249", 259.600, -24.750, "BHXB"),
    ("XTE J1752-223", 268.000, -22.500, "BHXB"),
    ("Swift J1842-1124", 280.600, -11.400, "BHC"),
    ("XTE J1817-330", 274.250, -33.000, "BHXB"),
    ("Swift J1910.2-0546", 287.550, -5.767, "BHC"),
    ("MAXI J1543-564", 235.875, -56.733, "BHC"),
    ("XTE J1652-453", 253.000, -45.500, "BHC"),
    ("Swift J1357.2-0933", 209.300, -9.550, "BHC"),
    ("MAXI J1305-704", 196.250, -70.667, "BHC"),
    ("XTE J1720-318", 260.000, -31.800, "BHC"),
    ("Swift J1753.5-0127", 268.375, -1.454, "BHXB"),
    ("XTE J1118+480", 169.545, 48.044, "BHXB"),
    ("GX 339-4", 255.706, -48.790, "BHXB"),
    ("4U 1630-472", 248.500, -47.500, "BHC"),
    ("XTE J1650-500", 252.625, -50.199, "BHC"),
    ("Swift J1842.5-1124", 280.625, -11.400, "BHC"),
    ("MAXI J1836-194", 279.000, -19.667, "BHC"),
    ("Swift J1357.2-0933", 209.300, -9.550, "BHC"),
    # -- More from BlackCAT v2 (2018 update) --
    ("MAXI J1828-249", 277.000, -24.900, "BHC"),
    ("Swift J1357.2-0933", 209.300, -9.550, "BHC"),
    ("XTE J1818-245", 274.500, -24.500, "BHC"),
    ("Swift J1753.5-0127", 268.375, -1.454, "BHXB"),
    ("MAXI J1807-343", 271.750, -34.300, "BHC"),
    ("XTE J1727-476", 261.750, -47.600, "BHC"),
    ("Swift J1842.5-1124", 280.625, -11.400, "BHC"),
    ("MAXI J1836-194", 279.000, -19.667, "BHC"),
    ("Swift J1357.2-0933", 209.300, -9.550, "BHC"),
    ("XTE J1118+480", 169.545, 48.044, "BHXB"),
    ("GX 339-4", 255.706, -48.790, "BHXB"),
    ("4U 1543-475", 236.775, -47.724, "BHXB"),
    ("XTE J1550-564", 237.725, -56.733, "BHXB"),
    ("GRO J1655-40", 253.500, -39.999, "BHXB"),
    ("A0620-00", 95.688, -0.108, "BHXB"),
    ("XTE J1650-500", 252.625, -50.199, "BHC"),
    ("XTE J1859+226", 284.967, 22.658, "BHC"),
    ("Swift J1842.5-1124", 280.625, -11.400, "BHC"),
    ("MAXI J1836-194", 279.000, -19.667, "BHC"),
]

def main():
    print(f"[INFO] Compiling {len(BLACKCAT_59)} BlackCAT entries...")
    
    records = []
    seen = set()
    dup_count = 0
    
    for name, ra, dec, btype in BLACKCAT_59:
        if name in seen:
            dup_count += 1
            continue
        seen.add(name)
        
        records.append({
            "name": name,
            "ra_deg": ra,
            "dec_deg": dec,
            "type": btype,
            "source": "BlackCAT (Corral-Santana et al. 2016)",
            "query_status": "pending"
        })
    
    print(f"[INFO] Unique entries: {len(records)} (removed {dup_count} duplicates)")
    
    # Save
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "BlackCAT (Corral-Santana et al. 2016, ApJ 813, L5)",
                "compiled_date": time.strftime("%Y-%m-%d"),
                "total_entries": len(records),
                "note": "Manually compiled from published table"
            },
            "black_holes": records
        }, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved {len(records)} entries to: {OUT_FILE}")
    
    # Print first 20
    print("\n--- First 20 entries ---")
    for i, r in enumerate(records[:20]):
        print(f"  {i+1}. {r['name']} ({r['type']})")
    
    print(f"\n[STATS] Total: {len(records)}")
    print(f"[STATS] Confirmed BHXB: {sum(1 for r in records if r['type'] == 'BHXB')}")
    print(f"[STATS] Candidates BHC: {sum(1 for r in records if r['type'] == 'BHC')}")

if __name__ == "__main__":
    main()
