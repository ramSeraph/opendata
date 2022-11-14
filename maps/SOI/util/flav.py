import glob
import json
from pathlib import Path

filenames = glob.glob('../data/inter/*/flav.txt')
flav_map = {}
for filename in filenames:
    print(f'processing {filename}')
    flav = Path(filename).read_text().strip()
    if flav not in flav_map:
        flav_map[flav] = []
    flav_map[flav].append(filename)

with open('flav_map.json', 'w') as f:
    json.dump(flav_map, f, indent = 2)
