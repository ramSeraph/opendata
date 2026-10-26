"""Assemble GitHub Pages with verified Parquets and the organization explorer.

No publication or Git mutation occurs here. The output is a deployable directory.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lgd-query' / 'src'))
sys.path.insert(0, str(ROOT))

from lgd_query import download, load_release
from lgd_query.metadata import Release
from lgd.visualizations.central_orgs.build import DATASETS, build as build_graph


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def checksum(content):
    return hashlib.sha256(content).hexdigest()


def category(name):
    if name.startswith(('central_', 'state_org', 'state_admin', 'org_unit')):
        return 'Organizations'
    if name in ('states', 'districts', 'subdistricts', 'blocks', 'villages', 'villages_by_blocks', 'invalidated_census_villages'):
        return 'Administrative areas'
    if 'constituenc' in name:
        return 'Constituencies'
    if name.startswith('pincode') or name == 'nofn_panchayats':
        return 'Postal & broadband'
    if name in ('changes', 'transactions'):
        return 'Change reports'
    return 'Local bodies'


def read_manifest(dataset, cache):
    path = cache / f'{dataset.name}.{dataset.manifest.sha256}.json'
    content = None
    if path.exists():
        cached = path.read_bytes()
        try:
            dataset.manifest.verify(cached)
        except ValueError:
            pass
        else:
            content = cached
    if content is None:
        # Retain the verified original bytes without a second HTTP request.
        from lgd_query._http import open_url
        with open_url(dataset.manifest.url, timeout=15) as response:
            content = response.read(dataset.manifest.size + 1)
        dataset.manifest.verify(content)
    manifest = json.loads(content)
    if manifest.get('kind') != 'lgd-daily-parquet' or manifest.get('format_version') != 1 or manifest.get('dataset') != dataset.name:
        raise ValueError(f'{dataset.name}: unexpected source manifest')
    for key in ('identity', 'representation', 'daily', 'coverage'):
        if manifest.get(key) != dataset.metadata.get(key):
            raise ValueError(f'{dataset.name}: manifest differs from pinned index: {key}')
    path.write_bytes(content)
    return manifest


def collect_dataset(dataset, cache):
    path = download(dataset, cache, timeout=15)
    manifest = read_manifest(dataset, cache)
    print(f'Verified {dataset.name}: {dataset.rows:,} rows, {dataset.parquet.size:,} bytes', flush=True)
    return dataset.name, (path, manifest)


def publish_data(release, collected, output, site_url):
    """Rewrite all public Parquet and manifest links to this Pages deployment."""
    destination = output / 'lgd' / 'data'
    destination.mkdir(parents=True, exist_ok=True)
    public = release.metadata
    public.pop('previous_index_url', None)
    public['upstream_generation'] = release.generation
    public['published_at'] = datetime.now(timezone.utc).isoformat()
    reports = {}
    for name, dataset in release.datasets.items():
        if not dataset.available:
            continue
        path, original = collected[name]
        filename = f'{name}.{dataset.parquet.sha256[:16]}.parquet'
        shutil.copyfile(path, destination / filename)
        entry = public['datasets'][name]
        entry['daily']['file']['url'] = f'{site_url}/lgd/data/{filename}'
        manifest = dict(original, daily=entry['daily'])
        content = encoded(manifest)
        manifest_hash = checksum(content)
        manifest_name = f'{name}.{manifest_hash[:16]}.json'
        (destination / manifest_name).write_bytes(content)
        entry['manifest'] = {'url': f'{site_url}/lgd/data/{manifest_name}',
                             'size': len(content), 'sha256': manifest_hash}
        if name in DATASETS:
            reports[name] = {
                'path': str(path), 'file': filename, 'date': dataset.observed_on.isoformat(),
                'parquet_sha256': dataset.parquet.sha256, 'manifest_sha256': manifest_hash,
                'source': original.get('source'), 'sha256': original.get('csv_sha256'),
                'source_row_count': original.get('conversion', {}).get('source_rows', dataset.rows),
                'publication_status': dataset.status,
            }
    public['generation'] = 'pages.' + checksum(encoded(public))[:24]
    public['immutable_url'] = f'{site_url}/lgd/data/metadata.{public["generation"]}.json'
    content = encoded(public)
    (destination / 'metadata.json').write_bytes(content)
    (destination / f'metadata.{public["generation"]}.json').write_bytes(content)
    # The same reader must accept the rewritten metadata; downloads retain their hashes.
    Release.from_dict(public)
    return public, reports


def build(output, cache, *, site_url, metadata=None):
    output, cache = output.resolve(), cache.resolve()
    source = ROOT / 'docs'
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('Build into a separate directory, not the authored docs tree')
    if output.exists() and any(output.iterdir()):
        raise ValueError(f'Output is not empty: {output}. Use a fresh build directory.')
    cache.mkdir(parents=True, exist_ok=True)
    release = (Release.from_dict(json.loads(metadata.read_text())) if metadata else load_release(timeout=15))
    for name in DATASETS:
        release.dataset(name)  # Fail before producing a partial explorer if an input is unavailable.
    available = [d for d in release.datasets.values() if d.available]
    with ThreadPoolExecutor(max_workers=4) as pool:
        collected = dict(pool.map(lambda d: collect_dataset(d, cache), available))
    shutil.copytree(source, output, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.gitignore', '.DS_Store', 'README.md'))
    shutil.copyfile(ROOT / 'lgd' / 'scrape' / 'site_map.json', output / 'lgd' / 'site_map.json')
    public, reports = publish_data(release, collected, output, site_url.rstrip('/'))
    scopes = build_graph(ROOT / 'lgd' / 'data', output / 'lgd' / 'organizations', reports=reports, web=True)
    site_map = json.loads((source.parent / 'lgd' / 'scrape' / 'site_map.json').read_text())
    descriptions = {r['file'].removesuffix('.csv'): r.get('desc', '') for r in site_map if r.get('file')}
    catalogue = {'published_at': public['published_at'], 'generation': public['generation'],
                 'metadata': 'data/metadata.json', 'datasets': [], 'scopes': scopes['scopes']}
    for name, dataset in release.datasets.items():
        entry = public['datasets'][name]
        manifest = collected[name][1] if dataset.available else {}
        catalogue['datasets'].append({
            'name': name, 'description': descriptions.get(name, name.replace('_', ' ')),
            'category': category(name), 'rows': dataset.rows,
            'observed_on': dataset.observed_on.isoformat() if dataset.observed_on else None,
            'representation': dataset.representation, 'status': dataset.status, 'reason': dataset.reason,
            'bytes': dataset.parquet.size if dataset.available else 0,
            'file': 'data/' + entry['daily']['file']['url'].rsplit('/', 1)[-1] if dataset.available else None,
            'manifest': 'data/' + entry['manifest']['url'].rsplit('/', 1)[-1] if dataset.available else None,
            'fields': manifest.get('schema', []),
        })
    (output / 'lgd' / 'catalogue.json').write_bytes(encoded(catalogue))
    (output / '.nojekyll').touch()
    total_bytes = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    summary = {'output': str(output), 'datasets': len(available), 'governments': len(scopes['scopes']),
               'parquet_bytes': sum(d.parquet.size for d in available), 'artifact_bytes': total_bytes,
               'upstream_generation': release.generation}
    (output / 'build.json').write_bytes(encoded(summary))
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.pages-build')
    parser.add_argument('--cache-dir', type=Path, default=ROOT / 'lgd' / 'data' / 'pages-cache')
    parser.add_argument('--metadata', type=Path, help='Use a previously pinned release index')
    parser.add_argument('--site-url', default='https://ramseraph.github.io/opendata')
    args = parser.parse_args()
    build(args.output, args.cache_dir, site_url=args.site_url, metadata=args.metadata)
