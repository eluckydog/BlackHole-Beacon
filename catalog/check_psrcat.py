import csv

with open('psrcat_catalog.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print('Total pulsars:', len(rows))

fields = ['P0_s', 'DM', 'S1400_mJy', 'W50_ms', 'RA_deg', 'Dec_deg']
counts = {}
for k in fields:
    counts[k] = sum(1 for r in rows if r.get(k, '').strip() != '')

print('\nField completeness:')
for k in fields:
    print(f'  {k}: {counts[k]} / {len(rows)} ({100*counts[k]/len(rows):.1f}%)')

# How many have ALL 6 fields?
all6 = sum(1 for r in rows if all(r.get(k, '').strip() != '' for k in fields))
print(f'\nPulsars with ALL 6 fields: {all6} / {len(rows)} ({100*all6/len(rows):.1f}%)')

# Show 3 samples
print('\n3 sample pulsars:')
for i in [0, 100, 1000]:
    if i < len(rows):
        r = rows[i]
        name = r.get('JName', '?')
        p0 = r.get('P0_s', '?')
        dm = r.get('DM', '?')
        ra = r.get('RA_deg', '?')
        dec = r.get('Dec_deg', '?')
        print(f'  [{i}] JName={name}, P0={p0}, DM={dm}, RA={ra}, Dec={dec}')
