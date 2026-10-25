"""Publish standalone daily Parquet reports; orchestration stays outside the converter."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid

from parquet.registry import SCHEMAS
from .parquet_release import GitHub, RELEASE, RELEASE_PATTERN, encoded, location, write_json
from .workflow_common import digest, output


DEPENDENCY = 'duckdb==2.0.0'
KIND = 'lgd-daily-parquet'
RAW_RELEASE = re.compile(r'lgd-latest(?:-.*)?')
DAILY_NAME = re.compile(r'([a-z_]+)\.([0-9]{2})([A-Z][a-z]{2})([0-9]{4})\.csv\.7z')
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
EVENTS = {'changes', 'transactions'}
DISCREPANCY_DATASETS = {
    'pri_local_body_wards', 'constituency_coverage',
    'constituencies_mapping_pri', 'parliament_constituencies_lb_mapping',
}


def fingerprint(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def converter_version():
    root = Path(__file__).resolve().parents[1]
    files = {p.name: digest(p) for p in sorted((root/'parquet').glob('*.py'))}
    publisher = {name: digest(root/'utils'/name) for name in ('parquet_workflow.py', 'parquet_release.py')}
    return dict(sha256=fingerprint(dict(files=files, dependency=DEPENDENCY)),
                publisher_sha256=fingerprint(publisher), dependency=DEPENDENCY)


def pin(asset, release):
    return {**{k: asset.get(k) for k in ('id', 'name', 'size', 'digest', 'updated_at', 'state',
                                       'browser_download_url')}, 'release': release}


def inventory(client):
    return [pin(a, tag) for tag, release in client.listed.items()
            if RAW_RELEASE.fullmatch(tag) and not release.get('draft')
            for a in client.release_assets(tag, refresh=True).values()
            if a['state'] == 'uploaded' and a['size'] > 0]


def newest_source(dataset, assets, *, through=None):
    candidates = []
    for asset in assets:
        match = DAILY_NAME.fullmatch(asset['name'])
        if match and match[1] == dataset:
            day = date(int(match[4]), MONTHS.index(match[3]) + 1, int(match[2])).isoformat()
            if through is not None and day > through:
                continue
            candidates.append((day, asset))
        elif dataset in EVENTS and asset['name'] == f'{dataset}.csv.7z':
            candidates.append((asset['updated_at'], asset))
    if not candidates:
        return None
    newest = max(day for day, _ in candidates)
    matching = [a for day, a in candidates if day == newest]
    if len(matching) > 1 and (not matching[0]['digest'] or
                              len({(a['size'], a['digest']) for a in matching}) != 1):
        raise ValueError(f'Ambiguous source files for {dataset} at {newest}')
    asset = sorted(matching, key=lambda a: (a['release'], a['id']))[0]
    coverage = None
    if dataset in EVENTS:
        found = [a for a in assets if a['name'] == f'{dataset}_dates_covered.txt'
                 and a['release'] == asset['release']]
        if len(found) != 1:
            raise ValueError(f'Missing/ambiguous coverage ledger for {dataset}')
        coverage = found[0]
    return dict(asset=asset, coverage=coverage,
                observed_on=None if dataset in EVENTS else newest,
                uploaded_at=asset['updated_at'], member=asset['name'][:-3])


def validate_index(index, repo):
    if (index.get('kind') != KIND or index.get('format_version') != 1 or
            index.get('repository') != repo or not isinstance(index.get('datasets'), dict)):
        raise ValueError('Unrecognized Parquet discovery format/repository')
    for name, entry in index['datasets'].items():
        if name not in SCHEMAS:
            raise ValueError(f'Unrecognized published dataset: {name}')
        if entry.get('manifest'):
            location(repo, entry['manifest'])
            location(repo, entry['daily']['file'])
    return index


def allocate(client, datasets):
    # Leave room for the two mutable discovery assets and interrupted uploads.
    counts = {tag: len(client.release_assets(tag)) for tag, release in client.listed.items()
              if RELEASE_PATTERN.fullmatch(tag) and not release.get('draft') and not release.get('immutable')}
    result = {}
    for name in [*sorted(datasets), '_index']:
        slots = 1 if name == '_index' else 3 if name in DISCREPANCY_DATASETS else 2
        tag = next((tag for tag in sorted(counts, key=lambda t: (t != RELEASE, t))
                    if counts[tag] + slots <= 980), None)
        if tag is None:
            number = 1
            while f'lgd-parquet-extra-{number:04}' in client.listed:
                number += 1
            raise ValueError('Insufficient release capacity; create '
                             f'lgd-parquet-extra-{number:04} manually and prepare a new run')
        counts[tag] += slots
        result[name] = tag
    return result


def prepare(client, datasets, commit):
    if not datasets or set(datasets) - SCHEMAS.keys():
        raise ValueError('Select known, nonempty dataset names')
    if not re.fullmatch('[a-f0-9]{40}', commit):
        raise ValueError('Pin a full converter commit')
    client.require_release(RELEASE)
    parent = client.read_index()
    if parent:
        validate_index(parent, client.repo)
    assets, version = inventory(client), converter_version()
    tasks, outcomes = {}, {}
    for name in sorted(set(datasets)):
        previous = (parent or {}).get('datasets', {}).get(name, {})
        try:
            source = newest_source(name, assets)
            if source is None:
                outcomes[name] = dict(status='unavailable', reason='No daily source is available')
                continue
            if (source['observed_on'] and previous.get('daily') and
                    source['observed_on'] < previous['daily']['observed_on']):
                outcomes[name] = dict(status='unavailable', reason='Available source predates published data')
                continue
            if name == 'pri_local_body_wards':
                source['name_reference'] = newest_source('pri_local_bodies', assets,
                                                          through=source['observed_on'])
            identity = fingerprint(dict(dataset=name, source=source, converter=version))
            if previous.get('identity') == identity:
                saved = client.read_json(client.verify_ref(previous['manifest']))
                client.verify_ref(previous['daily']['file'])
                evidence = saved.get('conversion', {}).get('discrepancy_evidence')
                if evidence:
                    client.verify_ref(evidence['file'])
                outcomes[name] = dict(status='unchanged')
                continue
            stamp = source['observed_on'] or source['uploaded_at'][:10]
            stem = f'{name}.{stamp}.{identity[:16]}'
            tasks[name] = dict(dataset=name, source=source, identity=identity,
                               parquet_name=stem+'.parquet', manifest_name=stem+'.json')
        except ValueError as error:
            outcomes[name] = dict(status='blocked', reason=str(error))
    allocation = allocate(client, tasks)
    for tag in set(allocation.values()):
        client.require_release(tag)
    for name, task in tasks.items():
        task['release'] = allocation[name]
        # Find an already uploaded candidate even if release allocation moved on.
        for tag in client.listed:
            if RELEASE_PATTERN.fullmatch(tag) and task['manifest_name'] in client.release_assets(tag):
                task['release'] = tag
                break
    now = datetime.now(timezone.utc)
    return dict(format_version=1, kind=KIND, repository=client.repo, parent=parent,
                commit=commit, converter=version, tasks=tasks, outcomes=outcomes,
                generation=now.strftime('%Y-%m-%dT%H%M%SZ')+'.'+uuid.uuid4().hex[:12],
                created_at=now.isoformat(), index_release=allocation['_index'])


def validate_plan(client, plan):
    if (plan['kind'] != KIND or plan['repository'] != client.repo or
            plan['converter'] != converter_version()):
        raise ValueError('Plan belongs to another repository/converter')


def candidate(client, plan, dataset):
    task = plan['tasks'][dataset]
    asset = client.release_assets(task['release']).get(task['manifest_name'])
    if not asset or asset['state'] != 'uploaded':
        return None
    manifest = client.read_json(asset)
    if (manifest.get('identity') != task['identity'] or manifest.get('dataset') != dataset or
            manifest.get('source') != task['source'] or manifest.get('converter') != plan['converter']):
        raise ValueError('Candidate identity/source differs from pinned plan')
    ref = dict(url=asset['browser_download_url'], size=asset['size'], sha256=fingerprint(manifest))
    client.verify_ref(ref)
    client.verify_ref(manifest['daily']['file'])
    evidence = manifest.get('conversion', {}).get('discrepancy_evidence')
    if evidence:
        client.verify_ref(evidence['file'])
    return manifest, ref


def check_sources(client, source):
    if source.get('name_reference'):
        check_sources(client, source['name_reference'])
    for expected in (source['asset'], source['coverage']):
        if expected is None:
            continue
        actual = client.release_assets(expected['release'], refresh=True).get(expected['name'])
        if not actual or pin(actual, expected['release']) != expected:
            raise ValueError('Source changed or was archived during conversion; retry with a fresh plan')


def event_coverage(connection, path, dataset, coverage_path):
    field = 'report_date' if dataset == 'changes' else 'transaction_date'
    fmt = '%d-%m-%Y' if dataset == 'changes' else '%Y-%m-%d'
    dates = sorted({datetime.strptime(line, fmt).date() for line in coverage_path.read_text().splitlines() if line})
    if not dates:
        raise ValueError('Empty event collection coverage')
    reported = [row[0] for row in connection.execute(
        f'SELECT DISTINCT {field} FROM read_parquet(?) ORDER BY 1', [str(path)]).fetchall()]
    if set(reported) - set(dates):
        raise ValueError('Event dates are outside the pinned collection coverage')
    return dict(first_event_date=str(reported[0]), last_event_date=str(reported[-1]),
                collected_dates=[str(day) for day in dates])


def worker(client, plan, dataset, work):
    validate_plan(client, plan)
    if candidate(client, plan, dataset):
        return
    # Nothing outside this function needs DuckDB or the scraping dependencies.
    import duckdb
    from parquet.convert import convert
    if 'duckdb=='+duckdb.__version__ != DEPENDENCY:
        raise ValueError('Worker DuckDB version differs from the publication plan')
    task, source = plan['tasks'][dataset], plan['tasks'][dataset]['source']
    check_sources(client, source)
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    required = source['asset']['size'] + 2 * 1024**3
    if source.get('name_reference'):
        required += source['name_reference']['asset']['size']
    if shutil.disk_usage(work).free < required:
        raise ValueError('Insufficient disk for source download and 2 GiB reserve')
    with tempfile.TemporaryDirectory(prefix=dataset+'-', dir=work) as folder:
        folder = Path(folder)
        raw, parquet = folder/source['asset']['name'], folder/task['parquet_name']
        client.download(source['asset'], raw)
        kwargs = {}
        reference = source.get('name_reference')
        if reference:
            reference_raw = folder/reference['asset']['name']
            reference_parquet = folder/'pri-reference.parquet'
            client.download(reference['asset'], reference_raw)
            reference_receipt = convert('pri_local_bodies', reference_raw, reference_parquet,
                member=reference['member'], observed_on=reference['observed_on'])
            kwargs = dict(pri_reference=reference_parquet,
                          reference_observed_on=reference['observed_on'])
        receipt = convert(dataset, raw, parquet, member=source['member'],
                          memory_limit='1GB', max_temp_size='2GB', threads=2,
                          observed_on=source['observed_on'], **kwargs)
        if reference:
            receipt['name_reference'].pop('path')
            receipt['name_reference']['csv_sha256'] = reference_receipt['source']['csv_sha256']
            receipt['name_reference']['container_sha256'] = reference_receipt['source']['sha256']
        coverage = None
        if source['coverage']:
            ledger = folder/source['coverage']['name']
            client.download(source['coverage'], ledger)
            with duckdb.connect(config={'threads': 2, 'memory_limit': '512MB'}) as connection:
                coverage = event_coverage(connection, parquet, dataset, ledger)
            coverage['source_sha256'] = digest(ledger)
        check_sources(client, source)
        ref = client.put(task['release'], parquet)
        if receipt.get('discrepancy_evidence'):
            evidence = receipt['discrepancy_evidence']
            receipt['discrepancy_evidence'] = dict(rows=evidence['rows'],
                file=client.put(task['release'], Path(evidence['path'])))
        manifest = dict(format_version=1, kind=KIND, dataset=dataset, identity=task['identity'],
                        source=source, converter=plan['converter'], converter_commit=plan['commit'],
                        representation='events' if dataset in EVENTS else 'snapshot',
                        daily=dict(observed_on=source['observed_on'], uploaded_at=source['uploaded_at'],
                                   file=ref, rows=receipt['rows']), coverage=coverage,
                        schema=[dict(id=i, name=n, type=t) for i, n, t, _ in SCHEMAS[dataset]],
                        conversion={k: v for k, v in receipt.items() if k not in ('source', 'output')},
                        csv_sha256=receipt['source']['csv_sha256'], container_sha256=receipt['source']['sha256'])
        path = folder/task['manifest_name']
        write_json(path, manifest)
        client.put(task['release'], path)


def verify_index(client, index):
    validate_index(index, client.repo)
    for dataset, entry in index['datasets'].items():
        if entry.get('manifest'):
            asset = client.verify_ref(entry['manifest'])
            manifest = client.read_json(asset)
            if (manifest['dataset'] != dataset or manifest['daily'] != entry['daily'] or
                    manifest['identity'] != entry['identity']):
                raise ValueError('Index differs from its dataset manifest')
            client.verify_ref(entry['daily']['file'])
            evidence = manifest.get('conversion', {}).get('discrepancy_evidence')
            if evidence:
                client.verify_ref(evidence['file'])


def publish(client, plan, work):
    validate_plan(client, plan)
    current = client.read_index()
    same_plan = current is not None and current.get('plan_sha256') == fingerprint(plan)
    if same_plan:
        # A previous attempt may have published only the successful workers.
        # Reconcile newly completed candidates before deciding this is a no-op.
        verify_index(client, current)
    elif fingerprint(current) != fingerprint(plan['parent']):
        raise ValueError('Publication parent changed; prepare a fresh plan')
    entries = dict((current or {}).get('datasets', {}))
    for dataset, outcome in plan['outcomes'].items():
        entries[dataset] = dict(entries.get(dataset, {}), outcome=outcome)
    for dataset in plan['tasks']:
        try:
            result = candidate(client, plan, dataset)
            if result is None:
                raise ValueError('Worker did not publish a verified result; see its job log')
            manifest, ref = result
            check_sources(client, plan['tasks'][dataset]['source'])
            entries[dataset] = {k: manifest[k] for k in ('identity', 'representation', 'daily', 'coverage')}
            entries[dataset].update(manifest=ref, outcome=dict(status='updated'))
        except (ValueError, subprocess.CalledProcessError) as error:
            entries[dataset] = dict(entries.get(dataset, {}), outcome=dict(status='failed', reason=str(error)))
    if current and entries == current['datasets']:
        return current
    now = datetime.now(timezone.utc)
    # Never overwrite the immutable index advertised by the preceding attempt.
    generation = (now.strftime('%Y-%m-%dT%H%M%SZ')+'.'+uuid.uuid4().hex[:12]
                  if same_plan else plan['generation'])
    filename = f'metadata.{generation}.json'
    index = dict(format_version=1, kind=KIND, repository=client.repo, generation=generation,
                 plan_sha256=fingerprint(plan),
                 published_at=now.isoformat(), converter_commit=plan['commit'],
                 immutable_url=f'https://github.com/{client.repo}/releases/download/{plan["index_release"]}/{filename}',
                 previous_index_url=current['immutable_url'] if current else None,
                 datasets=entries, automatic_deletion=False)
    verify_index(client, index)
    work = Path(work)
    write_json(work/filename, index)
    client.put(plan['index_release'], work/filename)
    if current:
        write_json(work/'metadata.previous.json', current)
        client.put(RELEASE, work/'metadata.previous.json', mutable=True)
    # On first publication our newly uploaded immutable index exists before
    # metadata.json. Distinguish that expected gap from an interrupted old index.
    latest = client.release_assets(RELEASE, refresh=True)
    actual = client.read_json(latest['metadata.json']) if 'metadata.json' in latest else None
    if fingerprint(actual) != fingerprint(current):
        raise ValueError('Publication parent changed before index replacement')
    write_json(work/'metadata.json', index)
    client.put(RELEASE, work/'metadata.json', mutable=True)
    return index


def recover(client, work):
    client.require_release(RELEASE)
    # Prefer complete immutable generations; never guess from a partial worker.
    snapshots = [(a['created_at'], a) for tag in client.listed if RELEASE_PATTERN.fullmatch(tag)
                 for name, a in client.release_assets(tag).items()
                 if re.fullmatch(r'metadata\.[0-9].*\.json', name) and a['state'] == 'uploaded']
    for _, asset in sorted(snapshots, key=lambda item: (item[0], item[1]['id']), reverse=True):
        try:
            index = client.read_json(asset)
            verify_index(client, index)
        except (ValueError, subprocess.CalledProcessError):
            continue
        path = Path(work)/'metadata.json'
        write_json(path, index)
        client.put(RELEASE, path, mutable=True)
        return index
    raise ValueError('No verified complete metadata generation is available to recover')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'check', 'worker', 'publish', 'recover'))
    parser.add_argument('--work', type=Path, default=Path('data/parquet-publication'))
    parser.add_argument('--dataset')
    parser.add_argument('--datasets', nargs='+', default=sorted(SCHEMAS))
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', 'ramSeraph/opendata'))
    args = parser.parse_args()
    client = GitHub(args.repository)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    path = args.work/'plan.json'
    if args.command == 'prepare':
        plan = prepare(client, args.datasets, commit)
        write_json(path, plan)
        if os.environ.get('GITHUB_OUTPUT'):
            output('matrix', dict(dataset=sorted(plan['tasks'])))
            output('has_work', 'true' if plan['tasks'] else 'false')
            output('commit', commit)
        print(json.dumps(dict(convert=sorted(plan['tasks']), outcomes=plan['outcomes']), indent=2))
    elif args.command == 'recover':
        recover(client, args.work)
    else:
        plan = json.loads(path.read_bytes())
        validate_plan(client, plan)
        if args.command == 'check':
            done = candidate(client, plan, args.dataset) is not None
            output('done', 'true' if done else 'false')
        elif args.command == 'worker':
            worker(client, plan, args.dataset, args.work)
        else:
            index = publish(client, plan, args.work)
            summary = '\n'.join(f'- {name}: {entry["outcome"]["status"]}; '
                                f'date: {entry.get("daily", {}).get("observed_on") or "see event coverage"}'
                                for name, entry in sorted(index['datasets'].items())) + '\n'
            print(summary)
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as target:
                    target.write(summary)
            selected = set(plan['tasks']) | set(plan['outcomes'])
            if any(index['datasets'][name]['outcome']['status'] in ('failed', 'blocked') for name in selected):
                raise SystemExit(1)


if __name__ == '__main__':
    main()
