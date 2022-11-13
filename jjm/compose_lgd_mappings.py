import csv

from pathlib import Path
from pprint import pprint

if __name__ == '__main__':
    mappings_dir = Path('data/lgd_mapping')
    files = mappings_dir.glob('**/*.csv')
    files_by_type = {}
    for file in files:
        parts = str(file).split('/')
        typ = parts[3]
        if typ not in files_by_type:
            files_by_type[typ] = []
        files_by_type[typ].append(file)

    pprint(files_by_type.keys())
    mappings_composed_dir = Path('data/lgd_mapping_composed')
    mappings_composed_dir.mkdir(exist_ok=True, parents=True)
    for key, files in files_by_type.items():
        composed_file = mappings_composed_dir / f'{key}.csv'
        print(f'filling in {composed_file}')
        wr = None
        with open(composed_file, 'w') as f:
            for file in files:
                print(f'reading {file}')
                with open(file, 'r') as rfp:
                    reader = csv.DictReader(rfp)
                    for row in reader:
                        if wr is None:
                            wr = csv.DictWriter(f, fieldnames=list(row.keys()))
                            wr.writeheader()
                        wr.writerow(row)
        
        
        
