import json
from pathlib import Path


def collect_status():
    status = {}
    for path in sorted(Path('reports').glob('*.json')):
        if path.name == 'status.json':
            continue
        entity = path.stem.removesuffix('s')
        report = json.loads(path.read_text())
        status[entity] = sum(len(entries) for entries in report.values())
    Path('reports').mkdir(exist_ok=True)
    Path('reports/status.json').write_text(json.dumps(status))
    return status


if __name__ == '__main__':
    print(collect_status())
