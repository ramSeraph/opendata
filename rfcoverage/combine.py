import csv
from datetime import datetime

def get_date_str():
    date = datetime.today()
    date_str = date.strftime("%d%b%Y")
    return date_str


def get_map(file):
    keys = None
    all_map = {}
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rkeys = list(r.keys())
            keys = rkeys
            rkeys = [ rk for rk in rkeys if rk != 'scrape_date' ]
            k = tuple([r[rk] for rk in rkeys])
            if k not in all_map:
                all_map[k] = r['scrape_date']
    return all_map, keys


def combine_network_files(prev_file, curr_file, comb_file):
    all_map = {}
    prev_map, prev_keys = get_map(prev_file)
    curr_map, curr_keys = get_map(curr_file)

    if prev_keys != curr_keys:
        raise Exception(f'data format mismatch - {prev_keys=}, {curr_keys=}')

    prev_set = set(prev_map.keys())
    curr_set = set(curr_map.keys())

    missing_in_curr = prev_set - curr_set
    missing_in_prev = curr_set - prev_set

    if len(missing_in_curr) > 0:
        raise Exception(f'{len(missing_in_curr)} entries missing in current data')
    print(f'{len(missing_in_prev)} entries being added')

    all_map.update(prev_map)
    for k,v in curr_map.items():
        if k not in all_map:
            all_map[k] = v

    print(f'writing {comb_file}')
    wr = None
    with open(comb_file, 'w') as f:
        for k, v in all_map.items():
            if wr is None:
                wr = csv.DictWriter(f, curr_keys)
                wr.writeheader()
            r = dict(zip(curr_keys, list(k) + [v]))
            wr.writerow(r)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--comp', help='which component to download', choices=['villages', 'network'], default='network')
    args = parser.parse_args()
    date_str = get_date_str()
    if args.comp == 'network':
        prev_file = 'data/network_data_old.csv'
        curr_file = f'data/{date_str}/network_data.csv'
        comb_file = 'data/network_data.csv'
        print(f'combining files {prev_file} {curr_file} into {comb_file}')
        combine_network_files(prev_file, curr_file, comb_file)




