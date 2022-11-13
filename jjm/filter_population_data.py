import json
import csv

hab_info_file = 'data/hab_info.jsonl'
pop_info_file = 'data/pop_info.csv'

count = 0
with open(pop_info_file, 'w') as fp:
    wr = csv.DictWriter(fp, fieldnames = ['hab_id', 'num_hh', 'pop_gen', 'pop_sc', 'pop_st'])
    wr.writeheader()
    with open(hab_info_file, 'r') as f:
        for line in f:
            count += 1
            if (count % 10000) == 0:
                print(f'done with {count}')
            data = json.loads(line)
            if 'error' in data:
                continue
            abstract_data = data['Abstract Data']
            pop_data = abstract_data["Total Population (As on 01/04/2022)"]
            filtered = {
                'hab_id': data['hab_id'],
                'num_hh': abstract_data['No. of Housesholds (As on 01/04/2022)'],
                'pop_gen': pop_data['GEN -'],
                'pop_sc': pop_data['SC -'],
                'pop_st': pop_data['ST -']
            }
            wr.writerow(filtered)


