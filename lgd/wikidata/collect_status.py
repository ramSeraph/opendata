import json
from pathlib import Path

status = {}
for p in Path('reports/').glob('*.json'):
    if p.name == 'status.json':
        continue
    entity = p.name.replace('s.json', '')
    print(f'Processing {entity}...')
    data = json.loads(p.read_text())
    l = 0
    for k,v in data.items():
        l += len(v)
    status[entity] = l
print(status)
Path('reports/status.json').write_text(json.dumps(status))
