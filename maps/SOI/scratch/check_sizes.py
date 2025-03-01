from pathlib import Path


MAX_SIZE = 10 * 1024 * 1024
lines = Path('b.txt').read_text().split('\n')
for line in lines:
    if line.strip() == '':
        continue
    parts = line.split(' ')
    sz = int(parts[1])
    if sz > MAX_SIZE:
        gpath = parts[-1]
        jpg = gpath.split('/')[-1]
        print(sz, jpg) 
    
