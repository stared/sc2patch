"""Find URLs for missing balance patches from CSV."""

import csv
import json
from pathlib import Path

# Read CSV to get all balance patches
csv_patches = []
with open('data/SC2_balance_patches_all.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_patches.append(row['Patch'])

# Read existing markdown files
md_patches = set()
for f in Path('data/raw_patches').glob('*.md'):
    md_patches.add(f.stem)

# Find missing patches
missing = sorted(set(csv_patches) - md_patches)

print(f"Missing {len(missing)} patches:")
print()

# Group by era
wol = [p for p in missing if p.startswith('1.')]
hots = [p for p in missing if p.startswith('2.')]
lotv_3 = [p for p in missing if p.startswith('3.')]
lotv_4 = [p for p in missing if p.startswith('4.')]
lotv_5 = [p for p in missing if p.startswith('5.')]

print(f"Wings of Liberty (1.x): {len(wol)} patches")
for p in wol:
    print(f"  - {p}")

print(f"\nHeart of the Swarm (2.x): {len(hots)} patches")
for p in hots:
    print(f"  - {p}")

print(f"\nLegacy of the Void (3.x): {len(lotv_3)} patches")
for p in lotv_3:
    print(f"  - {p}")

print(f"\nLegacy of the Void (4.x): {len(lotv_4)} patches")
for p in lotv_4:
    print(f"  - {p}")

print(f"\nLegacy of the Void (5.x): {len(lotv_5)} patches")
for p in lotv_5:
    print(f"  - {p}")

# Known URLs found so far
known_urls = {
    "5.0.9": "https://news.blizzard.com/en-us/article/23774006/starcraft-ii-5-0-9-ptr-patch-notes",
}

print(f"\n\nKnown URLs ({len(known_urls)}):")
for patch, url in known_urls.items():
    print(f"  {patch}: {url}")

print(f"\n\nNeed to find {len(missing) - len(known_urls)} more URLs")
