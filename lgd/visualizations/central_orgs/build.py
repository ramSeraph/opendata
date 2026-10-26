"""Build a Centre/state organization explorer from pinned latest Parquet exports."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil

import duckdb


HERE = Path(__file__).resolve().parent
LGD = HERE.parents[1]
KINDS = ('orgs', 'org_units', 'org_designations', 'admin_depts', 'admin_dept_units')
SHARED = ('org_unit_details', 'org_unit_coverage', 'states', 'districts')
DATASETS = tuple(f'{prefix}_{kind}' for prefix in ('central', 'state') for kind in KINDS) + SHARED
INTERNAL = {'source_schema_id', 'observed_from', 'observed_until'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str).encode()


def pin_sources(connection, data_dir):
    """Pin each manifest and its latest ledger once for all selections."""
    sources, ledgers, fields = {}, {}, {}
    for dataset in DATASETS:
        root = data_dir / f'{dataset}-history'
        raw = (root / 'iceberg.json').read_bytes()
        index = json.loads(raw)
        parquet = root / index['tables']['current']['parquet']
        connection.read_parquet(str(parquet)).create_view(dataset)
        fields[dataset] = [r[0] for r in connection.execute(f'DESCRIBE {dataset}').fetchall()
                           if r[0] not in INTERNAL]
        observation = root / index['tables']['observations']['parquet']
        ledger = connection.execute(
            'SELECT * FROM read_parquet(?) ORDER BY observed_on DESC LIMIT 1', [str(observation)])
        columns = [c[0] for c in ledger.description]
        latest = dict(zip(columns, ledger.fetchall()[0]))
        ledgers[dataset] = latest
        sources[dataset] = {
            'date': index['last_observation'],
            'file': str(Path(root.name) / parquet.name), 'parquet_sha256': digest(parquet),
            'manifest_sha256': hashlib.sha256(raw).hexdigest(),
            **{k: latest.get(k) for k in ('source', 'sha256', 'source_row_count')},
        }
    return sources, ledgers, fields


def pin_reports(connection, reports):
    """Open verified, current report snapshots supplied by the Pages build."""
    sources, fields = {}, {}
    for dataset in DATASETS:
        report = reports[dataset]
        parquet = Path(report['path'])
        if digest(parquet) != report['parquet_sha256']:
            raise ValueError(f'{dataset}: Parquet checksum changed before graph build')
        connection.read_parquet(str(parquet)).create_view(dataset)
        fields[dataset] = [r[0] for r in connection.execute(f'DESCRIBE {dataset}').fetchall()
                           if r[0] not in INTERNAL]
        sources[dataset] = {k: v for k, v in report.items() if k != 'path'}
    return sources, {dataset: {} for dataset in DATASETS}, fields


def scope_payload(connection, scope, sources, ledgers, fields, built_at):
    code = scope['code']
    if not re.fullmatch(r'[0-9]+', code):
        raise ValueError(f'Invalid selection code: {code}')
    prefix = 'central' if code == '0' else 'state'
    datasets = tuple(f'{prefix}_{kind}' for kind in KINDS) + SHARED
    payload = {'tables': {}, 'sources': {}, 'carried': {}, 'version': 2,
               'built_at': built_at, 'scope': scope}
    # Geographic lookup registers stay complete. State scope selects the owner
    # of an organization/unit, never a coverage target's geographic state.
    for dataset in datasets:
        selected = dataset not in ('states', 'districts') and 'state_code' in fields[dataset]
        where = f" WHERE state_code = '{code}'" if selected else ''
        connection.execute(f'CREATE OR REPLACE TEMP VIEW selected_{dataset} AS SELECT * FROM {dataset}{where}')
        columns = ', '.join('"' + f + '"' for f in fields[dataset])
        rows = connection.execute(f'SELECT {columns} FROM selected_{dataset}').fetchall()
        payload['tables'][dataset] = {'fields': fields[dataset], 'rows': rows}
        ids = {r[0] for r in rows}
        first = fields[dataset][0]
        records = [r for r in ledgers[dataset].get('carried_records') or []
                   if r.get(first) in ids and (not selected or r.get('state_code', code) == code)]
        scopes = [r for r in ledgers[dataset].get('carried_scopes') or []
                  if not selected or r.get('state_code') == code]
        payload['carried'][dataset] = {'records': records, 'scopes': scopes}
        payload['sources'][dataset] = {
            **sources[dataset], 'rows': len(rows), 'carried_forward_rows': len(records),
            'scope': f"{scope['name']} (state_code={code})" if dataset not in ('states', 'districts') else 'Complete geographic lookup register',
        }

    validation = {}
    for kind, key in (('orgs', 'organization_code'), ('org_units', 'organization_unit_code'),
                      ('admin_depts', 'administrative_unit_level_code')):
        dataset = f'{prefix}_{kind}'
        count, distinct = connection.execute(
            f'SELECT count(*), count(DISTINCT {key}) FROM selected_{dataset}').fetchall()[0]
        if count != distinct:
            raise ValueError(f'{dataset}, {scope["name"]}: duplicate {key}; graph identities need review')
        validation[dataset] = {'rows': count, 'distinct_ids': distinct}
    units = f'selected_{prefix}_org_units'
    for dataset in ('org_unit_details', 'org_unit_coverage'):
        validation[dataset] = {
            'scope_rows': payload['sources'][dataset]['rows'],
            'unit_ids_absent_from_directory': connection.execute(f'''
                SELECT count(DISTINCT d.organization_unit_code) FROM selected_{dataset} d
                WHERE NOT EXISTS (SELECT 1 FROM {units} u
                                  WHERE u.organization_unit_code=d.organization_unit_code)
            ''').fetchall()[0][0],
            'organization_disagreements': connection.execute(f'''
                SELECT count(*) FROM selected_{dataset} d JOIN {units} u USING(organization_unit_code)
                WHERE d.organization_code<>u.organization_code
            ''').fetchall()[0][0],
        }
    payload['validation'] = validation
    return payload


def write_shell(output, manifest, centre=None, *, web=False):
    """Refresh UI assets without rebuilding already verified scope bundles."""
    html = (HERE / 'index.html').read_text()
    for token, filename in (('/*__STYLE__*/', 'style.css'), ('/*__MODEL__*/', 'model.js'), ('/*__APP__*/', 'app.js')):
        if web:
            shutil.copyfile(HERE / filename, output / filename)
            asset = f'{filename}?v={digest(HERE / filename)[:12]}'
            if filename.endswith('.css'):
                html = html.replace(f'<style>{token}</style>', f'<link rel="stylesheet" href="{asset}">')
            else:
                html = html.replace(f'<script>{token}</script>', f'<script src="{asset}"></script>')
        else:
            html = html.replace(token, (HERE / filename).read_text())
    html = html.replace('__PAYLOAD__', '' if web else centre)
    if web:
        html = html.replace('<body>', '<body class="pages-explorer">')
        html = html.replace('<div class="brand"><span class="brand-mark">LGD</span>', '<div class="brand"><a class="brand-mark" href="../" aria-label="Back to LGD data">← LGD</a>')
        html = html.replace('</head>', '<meta name="description" content="Explore current LGD organizations, offices, designation titles, locations and coverage across Centre and states.">\n<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; object-src \'none\'; base-uri \'self\'">\n</head>')
        html = html.replace('The folder works offline. Nothing is uploaded.', 'Only the selected government’s data is loaded. Nothing is uploaded.')
    html = html.replace('__SCOPES__', json_bytes(manifest).decode().replace('<', '\\u003c'))
    (output / 'index.html').write_text(html)


def build(data_dir: Path, output: Path, *, reports=None, web=False):
    connection = duckdb.connect()
    connection.execute('SET threads=2')
    sources, ledgers, fields = (pin_reports(connection, reports) if reports is not None
                               else pin_sources(connection, data_dir))
    selections = [{'code': '0', 'name': 'Centre', 'kind': 'central'}] + [
        {'code': code, 'name': name, 'kind': 'state'} for code, name in
        connection.execute('SELECT state_code,state_name FROM states ORDER BY state_name').fetchall()
    ]
    known = {s['code'] for s in selections}
    for dataset in DATASETS:
        if 'state_code' in fields[dataset] and dataset not in ('states', 'districts'):
            reported = {r[0] for r in connection.execute(f'SELECT DISTINCT state_code FROM {dataset}').fetchall()}
            if reported - known:
                raise ValueError(f'{dataset}: states missing from selector register: {reported - known}')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'scopes').mkdir(exist_ok=True)
    built_at = datetime.now(timezone.utc).isoformat()
    entries, audits, centre = [], {}, None
    for scope in selections:
        payload = scope_payload(connection, scope, sources, ledgers, fields, built_at)
        packed = json_bytes(payload)
        compressed = gzip.compress(packed, compresslevel=9, mtime=0)
        prefix = 'central' if scope['code'] == '0' else 'state'
        filename = f"scopes/scope-{scope['code']}.js"
        encoded = base64.b64encode(compressed).decode()
        # Classic scripts work over file:// as well as HTTP; only the selected
        # scope is downloaded, decompressed and materialized into a graph.
        (output / filename).write_text(
            f'globalThis.LGDGraph.receiveScope({json.dumps(scope["code"])},{json.dumps(encoded)});\n')
        if not web:
            (output / f"scopes/scope-{scope['code']}.json.gz").write_bytes(compressed)
        entry = {**scope, 'file': filename, 'sha256': hashlib.sha256(compressed).hexdigest(),
                 'compressed_bytes': len(compressed), 'json_bytes': len(packed),
                 'organizations': payload['sources'][f'{prefix}_orgs']['rows'],
                 'units': payload['sources'][f'{prefix}_org_units']['rows'],
                 'designations': payload['sources'][f'{prefix}_org_designations']['rows']}
        entries.append(entry)
        audits[scope['code']] = {'scope': scope, 'sources': payload['sources'], 'checks': payload['validation']}
        if scope['code'] == '0':
            centre = encoded
            if not web:
                (output / 'data.json.gz').write_bytes(compressed)
        print(json.dumps(entry), flush=True)
    connection.close()
    manifest = {'version': 2, 'built_at': built_at, 'scopes': entries}
    write_shell(output, manifest, centre, web=web)
    (output / 'scopes.json').write_bytes(json_bytes(manifest) + b'\n')
    (output / 'validation.json').write_text(json.dumps({'built_at': built_at, 'scopes': audits}, indent=2, default=str) + '\n')
    print(json.dumps({'html': str((output / 'index.html').resolve()), 'scopes': len(entries),
                      'compressed_bytes': sum(e['compressed_bytes'] for e in entries)}, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=LGD / 'data')
    parser.add_argument('--output', type=Path, default=LGD / 'data' / 'central-org-graph')
    args = parser.parse_args()
    build(args.data_dir, args.output)
