import csv

def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

dups = {}
with open('data/facilities/water_sources.csv', 'w') as of:
    wr = None
    with open('data/facilities/water_sources_raw.csv', 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['hab_name'] == '':
                continue
            key = tuple(r.values())
            if key in dups:
                continue
            if wr is None:
                wr = csv.DictWriter(of, fieldnames=list(r.keys()))
                wr.writeheader()
            wr.writerow(r)



