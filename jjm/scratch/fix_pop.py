import csv

from scrape_population import special_cases, out_fields
print(special_cases)

new_name = 'data/hab_pop_hh.csv.new'
file_name = 'data/hab_pop_hh.csv'

with open(new_name, 'w') as wf:
    wr = csv.DictWriter(wf, fieldnames=out_fields)
    wr.writeheader()
    with open(file_name, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row['id']
            if rid not in special_cases:
                wr.writerow(row)
                continue
            data = special_cases[rid]
            if data is None:
                continue
            data['id'] = rid
            wr.writerow(data)
