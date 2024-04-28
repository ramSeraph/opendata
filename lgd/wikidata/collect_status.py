import json
from pathlib import Path

status = {}
for p in Path('reports/').glob('*.json'):
    entity = p.name.replace('s.json', '')
    data = json.loads(p.read_text())
    l = 0
    for k,v in data.items():
        l += len(v)
    status[entity] = l
print(status)
Path('reports/status.json').write_text(json.dumps(status))
