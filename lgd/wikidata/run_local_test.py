"""Foreground test of the download and report stages; never publishes reports."""

import argparse
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import time
from datetime import datetime

import raw_wikidata


DATASETS = {
    'states': 'Q131541',
    'divisions': 'Q1230708',
    'districts': 'Q1149652',
    'subdivisions': 'Q7631016',
    'subdistricts': 'Q105626471',
    'district_panchayats': 'Q2758248',
}
LGD_FILES = ('district_panchayats', 'districts', 'pri_local_bodies', 'states', 'subdistricts')
DEPENDENCIES = {
    'states': ('states',),
    'divisions': ('states', 'divisions', 'districts'),
    'districts': ('states', 'divisions', 'districts'),
    'subdivisions': ('districts', 'subdivisions', 'subdistricts'),
    'subdistricts': ('districts', 'subdivisions', 'subdistricts'),
    'district_panchayats': ('states', 'districts', 'district_panchayats'),
}


def get_inputs():
    session = raw_wikidata.client.session
    listing_url = 'https://github.com/ramSeraph/opendata/releases/download/lgd-latest/listing_files.csv'
    response = session.get(listing_url, timeout=(10, 90))
    response.raise_for_status()
    rows = list(csv.reader(io.StringIO(response.text)))
    directory = Path('data/lgd')
    directory.mkdir(parents=True, exist_ok=True)
    for prefix in LGD_FILES:
        choices = [row for row in rows if row[0].startswith(prefix + '.')]
        row = max(choices, key=lambda row: datetime.strptime(row[0].split('.')[1], '%d%b%Y'))
        filename, _, url = row
        date = filename.split('.')[1]
        output = directory / f'{prefix}.csv'
        datefile = Path('data') / f'{prefix}.lgd_date.txt'
        if output.exists() and datefile.exists() and datefile.read_text().strip() == date:
            print(f'LGD {prefix}: reusing {date}', flush=True)
            continue
        archive = directory / filename
        with session.get(url, stream=True, timeout=(10, 90)) as response:
            response.raise_for_status()
            with archive.with_suffix('.tmp').open('wb') as stream:
                for chunk in response.iter_content(1024 * 1024):
                    stream.write(chunk)
        archive.with_suffix('.tmp').replace(archive)
        temporary = output.with_suffix('.csv.tmp')
        with temporary.open('wb') as stream:
            subprocess.run(['7z', 'x', '-so', str(archive), filename.removesuffix('.7z')],
                           stdout=stream, check=True)
        temporary.replace(output)
        datefile.write_text(date + '\n')
        archive.unlink()
        print(f'LGD {prefix}: {date}, {output.stat().st_size:,} bytes', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interactive', action='store_true',
                        help='Omit optional maxlag for a foreground user-requested test only')
    parser.add_argument('--download-only', action='store_true')
    parser.add_argument('--reports-only', action='store_true')
    parser.add_argument('--keep-going', action='store_true', help='Record report failures and test the remaining checkers')
    parser.add_argument('--datasets', nargs='+', choices=DATASETS, default=list(DATASETS))
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parent)
    if args.interactive:
        raw_wikidata.client.maxlag = None
        print('Foreground interactive test: optional maxlag omitted; pacing and HTTP retries remain enabled.', flush=True)
    start = time.monotonic()
    results = {'downloads': {}, 'reports': {}}
    needed = set(args.datasets) if args.download_only else {
        dependency for dataset in args.datasets for dependency in DEPENDENCIES[dataset]
    }
    if args.reports_only:
        missing = [dataset for dataset in needed if not Path(f'data/{dataset}.jsonl').exists()]
        if missing:
            parser.error(f'Reports require these downloads first: {", ".join(sorted(missing))}')
    for dataset in ([] if args.reports_only else [name for name in DATASETS if name in needed]):
        print(f'Discovering {dataset}...', flush=True)
        before = time.monotonic()
        count = raw_wikidata.download_query(
            f'SELECT ?item WHERE {{ ?item wdt:P31/wdt:P279* wd:{DATASETS[dataset]}. }}',
            f'data/{dataset}.jsonl')
        results['downloads'][dataset] = {'count': count, 'seconds': round(time.monotonic() - before, 2)}
        print(json.dumps({dataset: results['downloads'][dataset]}), flush=True)
    if not args.download_only:
        get_inputs()
        for dataset in args.datasets:
            print(f'Checking {dataset}...', flush=True)
            before = time.monotonic()
            captured = io.StringIO()
            try:
                with contextlib.redirect_stdout(captured):
                    runpy.run_path(f'check_{dataset}.py', run_name='__main__')
            except Exception as error:
                print('\n'.join(captured.getvalue().splitlines()[-12:]), flush=True)
                if not args.keep_going:
                    raise
                results['reports'][dataset] = {
                    'seconds': round(time.monotonic() - before, 2),
                    'error': f'{type(error).__name__}: {error}',
                }
                print(json.dumps({dataset: results['reports'][dataset]}), flush=True)
                continue
            report = json.loads(Path(f'reports/{dataset}.json').read_text())
            results['reports'][dataset] = {
                'seconds': round(time.monotonic() - before, 2),
                'findings': sum(len(entries) for entries in report.values()),
                'categories': {key: len(value) for key, value in report.items() if value},
            }
            print(json.dumps({dataset: results['reports'][dataset]}), flush=True)
        runpy.run_path('collect_status.py', run_name='__main__')
    results.update(seconds=round(time.monotonic() - start, 2),
                   wikidata_requests=raw_wikidata.client.requests,
                   wikidata_bytes=raw_wikidata.client.bytes)
    Path('data/local-test-result.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2), flush=True)
    if any('error' in report for report in results['reports'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
