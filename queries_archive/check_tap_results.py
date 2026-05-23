import json
from pathlib import Path

JSON_FILE = Path(r"C:\Users\13918\.qclaw\workspace-math-science\projects\blackhole-beacon\data\all_known_bh_xrb_tap.json")

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total records: {len(data['records'])}")
print(f"\n--- First 20 records ---")
for i, r in enumerate(data["records"][:20]):
    print(f"  {i+1}. {r['main_id']} (otype={r['otype']})")

# Check how many have "BH" in main_id
bh_in_name = [r for r in data["records"] if "BH" in r["main_id"].upper() or "BLACK" in r["main_id"].upper()]
print(f"\n[STATS] Records with 'BH' in name: {len(bh_in_name)}")

if bh_in_name:
    print(f"\n--- First 10 BH-named records ---")
    for i, r in enumerate(bh_in_name[:10]):
        print(f"  {i+1}. {r['main_id']} (otype={r['otype']})")
