import csv

def truncate(fname):
    tfname = fname.replace('.csv', '_truncated.csv')
    with open(tfname, 'w') as wf:
        wr = None
        with open(fname, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                if wr is None:
                    wr = csv.DictWriter(f, list(r.keys()))
                    wr.writeheader()
                r['longitude'] = round(r['longitude'], 5)
                r['latitude'] = round(r['latitude'], 5)
                wr.writerow(r)

truncate('data/facilities/schools.csv')
truncate('data/facilities/anganwadis.csv')
