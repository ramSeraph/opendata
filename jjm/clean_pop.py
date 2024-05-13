import csv

fname_raw = 'data/hab_pop_raw.csv'
fname = 'data/hab_pop.csv'

with open(fname, 'w') as of:
    wr = None
    with open(fname_raw, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['hab_name'] == '':
                continue
            if wr is None:
                wr = csv.DictWriter(of, fieldnames=list(r.keys()))
                wr.writeheader()
            wr.writerow(r)
