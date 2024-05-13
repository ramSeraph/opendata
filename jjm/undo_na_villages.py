import csv
import os

fname = 'data/facilities/water_sources.csv'
fname_new = 'data/facilities/water_sources.csv.new'

states_to_undo = set()
dists_to_undo = set()
blocks_to_undo = set()
gps_to_undo = set()
vills_to_undo = set()
keys = None
with open(fname, 'r') as f:
    reader = csv.DictReader(f)
    for r in reader:
        if keys is None:
            keys = list(r.keys())
        if r['village_lgd_id'] != 'NA':
            continue
        states_to_undo.add(r['state_id'])
        dists_to_undo.add(r['dist_id'])
        blocks_to_undo.add(r['block_id'])
        gps_to_undo.add(r['gp_id'])
        vills_to_undo.add(r['village_id'])

with open(fname_new, 'w') as of:
    wr = csv.DictWriter(of, fieldnames=keys)
    wr.writeheader()
    with open(fname, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['village_lgd_id'] == 'NA':
                continue
            if r['village_lgd_id'] != '':
                wr.writerow(r)
                continue
            if r['village_id'] != '':
                if r['village_id'] not in vills_to_undo:
                    wr.writerow(r)
                continue
            if r['gp_id'] != '':
                if r['gp_id'] not in gps_to_undo:
                    wr.writerow(r)
                continue
            if r['block_id'] != '':
                if r['block_id'] not in blocks_to_undo:
                    wr.writerow(r)
                continue
            if r['dist_id'] != '':
                if r['dist_id'] not in dists_to_undo:
                    wr.writerow(r)
                continue
            if r['state_id'] != '':
                if r['state_id'] not in states_to_undo:
                    wr.writerow(r)
                continue


os.replace(fname_new, fname)


