import json
import csv
import glob
from pathlib import Path

if __name__ == '__main__':
    import sys
    folder_name = sys.argv[1]

    filenames = glob.glob(f'{folder_name}/*/*/*.json')
    out_filename = folder_name + '.csv'
    with open(out_filename, 'w') as f:
        #wr = csv.DictWriter()
        wr = None
        for filename in filenames:
            dist_name = Path(filename).parent.name
            state_name = Path(filename).parent.parent.name
            print(f'processing file: {filename}')
            with open(filename, 'r') as inp_f:
                data = json.load(inp_f)
                for entry in data:
                    new_entry = { 'state': state_name, 'ditrict': dist_name }
                    new_entry['block'] = entry.pop('block')
                    new_entry['gp'] = entry.pop('gp')
                    new_entry['village'] = entry.pop('village')
                    new_entry.update(entry)
                    if wr is None:
                        fieldnames = new_entry.keys()
                        wr = csv.DictWriter(f, fieldnames=fieldnames)
                        wr.writeheader()
                    wr.writerow(new_entry)


