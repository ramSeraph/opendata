import csv
import json

from pathlib import Path

def collect_hab_info():
    print('collecting hab info')
    entries = []
    paths = Path('data/habitations/').glob('*/*/*.json')
    for path in paths:
        rows = json.loads(path.read_text())
        entries += rows

    return entries

def collect_links():
    path = Path('data/village_links.csv')
    entries = collect_hab_info()
    seen = set()
    with open(path, 'w') as f:
        wr = csv.writer(f)
        wr.writerow(['village_id', 'link'])
        for e in entries:
            village_id = e['village_id']
            if village_id in seen:
                continue
            link = e['url']
            wr.writerow([ village_id, link ])
            seen.add(village_id)


def compose_habs_simple():
    entries = collect_hab_info()
    with open('data/habs.csv', 'w') as f:
        fieldnames = ['state_name', 'dist_name', 'block_name', 'gp_name', 'village', 'village_id', 'hab_name', 'hab_id', 'num_hh', 'num_hh_tap' ]
        wr = csv.DictWriter(f, fieldnames=fieldnames)
        wr.writeheader()
        for e in entries:
            del e['url']
            wr.writerow(e)

#collect_links()
compose_habs_simple()

