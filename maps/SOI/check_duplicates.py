
import sys
from pathlib import Path
from filecmp import cmp
from known_problems import known_problems

file_list = Path(sys.argv[1]).read_text().split('\n')
file_list = [ f'data/raw/{f.strip()}.pdf' for f in file_list if f.strip() != '' ]

file_map = {}
for filename in file_list:
    if filename in known_problems:
        continue
    is_a_copy = False
    for e_filename in file_map.keys():
        if cmp(e_filename, filename):
            file_map[e_filename].append(filename)
            is_a_copy = True
            break

    if is_a_copy:
        continue
    file_map[filename] = []

duplicate_map = {k:v for k,v in file_map.items() if len(v) != 0}
print(f'{duplicate_map=}')
if len(duplicate_map) > 0:
    exit(1)
exit(0)
