"""Command-line wrappers around the three public reader APIs."""

import argparse
import json
import math
import sys

from . import DEFAULT_METADATA_URL, connect, download, load_manifest, load_release


def _json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return 'NaN' if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            # Match DuckDB's representation for MAP keys that cannot be dict
            # keys. JSON objects would stringify keys and can lose identity.
            return {'key': [_json_value(key) for key in value],
                    'value': [_json_value(item) for item in value.values()]}
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _print(value):
    print(json.dumps(_json_value(value), ensure_ascii=False, default=str, allow_nan=False, indent=2))


def _rich():
    try:
        from rich.console import Console
        from rich.table import Column, Table
        from rich.text import Text
    except ImportError as error:
        raise ImportError('Table output requires: pip install "lgd-query[cli]"; '
                          'or use --format json') from error
    return Console, Column, Table, Text


def _table(columns, rows, *, title=None):
    Console, Column, Table, Text = _rich()
    table = Table(*(Column(Text(str(c))) for c in columns), title=Text(title) if title else None)
    for row in rows:
        table.add_row(*(Text('—' if value is None else str(value)) for value in row))
    Console().print(table)


def _query_output(cursor, format):
    columns = [column[0] for column in cursor.description]
    if format == 'table':
        # Bound Rich's table buffer as well as DuckDB's fetched row batches.
        batch = cursor.fetchmany(1000)
        _table(columns, batch)
        while batch := cursor.fetchmany(1000):
            _table(columns, batch)
    else:
        # Column/value arrays retain repeated column names in joins.
        sys.stdout.write('{"columns": ' + json.dumps(columns, ensure_ascii=False) + ', "rows": [')
        separator = ''
        while batch := cursor.fetchmany(1000):
            for row in batch:
                sys.stdout.write(separator + json.dumps(_json_value(row), ensure_ascii=False,
                                                       default=str, allow_nan=False))
                separator = ',\n'
        sys.stdout.write(']}\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read public LGD Parquet release data')
    parser.add_argument('--metadata-url', default=DEFAULT_METADATA_URL,
                        help='Current metadata or an immutable saved-generation URL')
    commands = parser.add_subparsers(dest='command', required=True)
    listing = commands.add_parser('list', help='List datasets, dates and availability')
    listing.add_argument('--available-only', action='store_true')
    resolve = commands.add_parser('resolve', help='Resolve a dataset to its immutable file references')
    resolve.add_argument('dataset')
    resolve.add_argument('--manifest', action='store_true', help='Also fetch and verify schema/source metadata')
    fetching = commands.add_parser('download', help='Download and verify selected Parquet files')
    fetching.add_argument('datasets', nargs='+')
    fetching.add_argument('--directory', required=True)
    querying = commands.add_parser('query', help='Run SQL over selected datasets')
    querying.add_argument('sql')
    querying.add_argument('--datasets', nargs='+', required=True)
    querying.add_argument('--cache-dir', help='Use verified local files instead of remote range reads')
    querying.add_argument('--params', help='SQL parameters as a JSON array or object')
    for command in (listing, resolve, fetching, querying):
        command.add_argument('--format', choices=('table', 'json'), default='table',
                             help='Output format (default: table, requires the cli extra)')
    for command in (resolve, fetching, querying):
        command.add_argument('--observed-on', help='Require this exact YYYY-MM-DD report date')
    args = parser.parse_args(argv)
    try:
        if args.format == 'table':
            _rich()  # Fail before metadata requests, downloads or SQL work.
        release = load_release(args.metadata_url)
        if args.command == 'list':
            result = dict(generation=release.generation, published_at=release.published_at,
                        immutable_url=release.immutable_url,
                        datasets=[dict(name=d.name, available=d.available, observed_on=d.observed_on,
                                       uploaded_at=d.uploaded_at, rows=d.rows,
                                       representation=d.representation, status=d.status, reason=d.reason)
                                  for d in release.datasets.values()
                                  if not args.available_only or d.available])
            if args.format == 'json':
                _print(result)
            else:
                _table(['Dataset', 'Observed on', 'Rows', 'Status'],
                       [(d['name'], d['observed_on'], d['rows'], d['status']) for d in result['datasets']],
                       title=f'LGD · {release.generation}')
        elif args.command == 'resolve':
            dataset = release.dataset(args.dataset, observed_on=args.observed_on)
            result = dict(generation=release.generation, immutable_url=release.immutable_url,
                          dataset=dataset.name, entry=dataset.metadata)
            if args.manifest:
                result['manifest'] = load_manifest(dataset)
            if args.format == 'json':
                _print(result)
            else:
                _table(['Field', 'Value'], [
                    ('Dataset', dataset.name), ('Representation', dataset.representation),
                    ('Observed on', dataset.observed_on), ('Uploaded at', dataset.uploaded_at),
                    ('Rows', dataset.rows), ('Outcome', dataset.status), ('Reason', dataset.reason),
                    ('Parquet URL', dataset.parquet.url), ('Bytes', dataset.parquet.size),
                    ('SHA-256', dataset.parquet.sha256), ('Manifest URL', dataset.manifest.url),
                    ('Generation', release.generation), ('Index URL', release.immutable_url),
                ])
                if args.manifest:
                    _table(['ID', 'Column', 'Type'],
                           [(f['id'], f['name'], f['type']) for f in result['manifest']['schema']],
                           title='Canonical schema')
        else:
            datasets = [release.dataset(name, observed_on=args.observed_on) for name in args.datasets]
            if args.command == 'download':
                result = [dict(dataset=d.name, observed_on=d.observed_on,
                               path=str(download(d, args.directory))) for d in datasets]
                if args.format == 'json':
                    _print(result)
                else:
                    _table(['Dataset', 'Observed on', 'Verified file'],
                           [(r['dataset'], r['observed_on'], r['path']) for r in result])
            else:
                params = json.loads(args.params) if args.params is not None else None
                if params is not None and not isinstance(params, (list, dict)):
                    raise ValueError('--params must be a JSON array or object')
                with connect(datasets, cache_dir=args.cache_dir) as connection:
                    cursor = connection.execute(args.sql, params)
                    _query_output(cursor, args.format)
    except Exception as error:
        parser.exit(1, f'lgd-query: {error}\n')
    return 0
