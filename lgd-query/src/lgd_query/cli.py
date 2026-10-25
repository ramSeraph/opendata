"""Command-line wrappers around the reader APIs and dataset queries."""

import argparse
import json
import math
import sys

from . import DEFAULT_METADATA_URL, connect, download, load_manifest, load_release
from .queries import districts as district_queries, states as state_queries
from .queries import subdistricts as subdistrict_queries
from .queries import DATASETS, get as query_module, sources as query_sources


_DATASET_QUERIES = {'states': state_queries, 'districts': district_queries,
                    'subdistricts': subdistrict_queries}


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
    console = Console()
    # Relationship reports can have twenty columns. A horizontal table at
    # ordinary terminal widths otherwise hides every name behind ellipses.
    if sum(min(len(str(c)), 20) + 3 for c in columns) > console.width:
        for index, row in enumerate(rows, 1):
            table = Table(Column('Field'), Column('Value'),
                          title=Text(f'{title + " · " if title else ""}Row {index}'))
            for column, value in zip(columns, row):
                table.add_row(Text(str(column)), Text('—' if value is None else str(value)))
            console.print(table)
        if not rows:
            console.print(Text('No matching rows.'))
        return
    table = Table(*(Column(Text(str(c))) for c in columns), title=Text(title) if title else None)
    for row in rows:
        table.add_row(*(Text('—' if value is None else str(value)) for value in row))
    console.print(table)


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


def _dataset_commands(commands, dataset):
    if dataset not in _DATASET_QUERIES:
        return _report_commands(commands, dataset)
    noun = {'states': 'state', 'districts': 'district', 'subdistricts': 'subdistrict'}[dataset]
    label = 'states and union territories' if dataset == 'states' else dataset
    group = commands.add_parser(dataset, help=f'List, look up and search {label}')
    actions = group.add_subparsers(dest='dataset_query', required=True)
    listing = actions.add_parser('list', help=f'List reported {label}')
    code = actions.add_parser('code', help=f'Look up an LGD {noun} code')
    code.add_argument('code')
    census = actions.add_parser('census-code', help=f'Look up a {noun} census code in one census year')
    census.add_argument('code')
    census.add_argument('--year', type=int, choices=(2001, 2011), required=True)
    search = actions.add_parser('search', help=f'Search reported {noun} names')
    search.add_argument('name')
    search.add_argument('--mode', choices=('exact', 'prefix', 'contains', 'fuzzy'), default='contains')
    search.add_argument('--max-distance', type=int, default=2,
                        help='Maximum fuzzy distance (UTF-8 byte edits; default: 2)')
    search.add_argument('--metric', choices=('levenshtein', 'damerau_levenshtein'), default='levenshtein')
    search.add_argument('--limit', type=int, default=20, help='Maximum results (default: 20)')
    if dataset == 'states':
        search.add_argument('--field', choices=('english', 'local'), default='english')
        for command in (listing, search):
            command.add_argument('--kind', choices=('state', 'ut'))
    else:
        for command in (listing, census, search):
            command.add_argument('--state-code', help='Restrict to this LGD state code')
            if dataset == 'subdistricts':
                command.add_argument('--district-code', help='Restrict to this LGD district code')
    for command in (listing, code, census, search):
        command.add_argument('--cache-dir', help='Use verified local files instead of remote range reads')
    return listing, code, census, search


def _dataset_result(connection, args):
    if args.command not in _DATASET_QUERIES:
        module = query_module(args.command)
        if args.dataset_query == 'eci-codes':
            return module.eci_codes(connection, level=args.level,
                constituency_code=args.constituency_code,state_code=args.state_code,eci_code=args.eci_code)
        filters = {key: getattr(args, key, None) for key in module.filters
                   if getattr(args, key, None) is not None}
        if getattr(args, 'include_entity_name', False):
            filters['include_entity_name'] = True
        if args.dataset_query in ('code', 'id'):
            method = module.by_id if args.dataset_query == 'id' else module.by_code
            return method(connection, args.lookup_code, **filters)
        if args.dataset_query == 'census-code':
            return module.by_census_code(connection, args.lookup_code, year=args.year, **filters)
        if args.dataset_query == 'list':
            return module.list(connection, **filters)
        if args.dataset_query == 'entities':
            return module.entities(connection, **filters)
        return module.search(connection, args.name, field=args.field, mode=args.mode,
                             max_distance=args.max_distance, metric=args.metric,
                             limit=args.limit, **filters)
    module = _DATASET_QUERIES[args.command]
    if args.dataset_query == 'code':
        return module.by_code(connection, args.code)
    filters = {} if args.command == 'states' else {'state_code': args.state_code}
    if args.command == 'subdistricts':
        filters['district_code'] = args.district_code
    if args.dataset_query == 'census-code':
        return module.by_census_code(connection, args.code, year=args.year, **filters)
    if args.command == 'states':
        filters['kind'] = args.kind
    if args.dataset_query == 'list':
        return module.list(connection, **filters)
    if args.command == 'states':
        filters['field'] = args.field
    return module.search(connection, args.name, mode=args.mode, max_distance=args.max_distance,
                         metric=args.metric, limit=args.limit, **filters)


def _report_commands(commands, dataset):
    module = query_module(dataset)
    spec = module._queries.spec
    group = commands.add_parser(dataset, help=f'Query {dataset.replace("_", " ")}')
    actions = group.add_subparsers(dest='dataset_query', required=True)
    listing = actions.add_parser('list', help='List supplied rows with exact column filters')
    action = 'id' if dataset == 'transactions' else 'code'
    lookup = actions.add_parser(action, help=f'Look up {spec.primary_code}; retain all matches')
    lookup.add_argument('lookup_code')
    search = actions.add_parser('search', help='Search names or a documented lookup field')
    search.add_argument('name')
    search.add_argument('--field', choices=module.name_fields, default='english')
    search.add_argument('--mode', choices=('exact', 'prefix', 'contains', 'fuzzy'), default='contains')
    search.add_argument('--metric', choices=('levenshtein', 'damerau_levenshtein'), default='levenshtein')
    search.add_argument('--max-distance', type=int, default=2, help='Maximum UTF-8 byte edit distance')
    search.add_argument('--limit', type=int, default=20)
    parsers = [listing, lookup, search]
    entities = None
    if hasattr(module, 'entities'):
        entities = actions.add_parser('entities', help='Follow typed entity codes to their register records')
        parsers.append(entities)
    if module.census_years:
        census = actions.add_parser('census-code', help='Look up the primary entity in one census namespace')
        census.add_argument('lookup_code')
        census.add_argument('--year', type=int, choices=module.census_years, required=True)
        parsers.append(census)
    for command in parsers:
        if dataset in ('state_org_units', 'central_org_units') and command is not entities:
            command.add_argument('--include-entity-name', action='store_true',
                                 help='Resolve location labels from org_unit_details')
        for column in module.filters:
            if command is lookup and column == spec.primary_code:
                continue
            if command is entities and column == getattr(module, 'entity_type_filter', 'entity_type'):
                command.add_argument('--'+column.replace('_', '-'),
                                     choices=getattr(module, 'entity_types', None), required=True,
                                     help='Exact source type; numeric location code or coverage type label')
                continue
            command.add_argument('--'+column.replace('_', '-'), dest=column,
                                 type=int if column in spec.integers else str,
                                 help=f'Exact {column} filter' if column not in ('since', 'until')
                                 else 'Inclusive event date (YYYY-MM-DD)')
        command.add_argument('--cache-dir', help='Use verified local files instead of remote range reads')
    if hasattr(module, 'eci_codes'):
        eci = actions.add_parser('eci-codes', help='Look up reported LGD/ECI mappings and ambiguity flags')
        eci.add_argument('--level', choices=module.eci_levels, required=True)
        eci.add_argument('--constituency-code', help='Exact LGD constituency code')
        eci.add_argument('--state-code', help='Exact LGD state code')
        eci.add_argument('--eci-code', help='Exact reported ECI code; retain every matching LGD code')
        eci.add_argument('--cache-dir', help='Use verified local files instead of remote range reads')
        parsers.append(eci)
    return parsers


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
    dataset_commands = tuple(command for name in DATASETS
                             for command in _dataset_commands(commands, name))
    for command in (listing, resolve, fetching, querying, *dataset_commands):
        command.add_argument('--format', choices=('table', 'json'), default='table',
                             help='Output format (default: table, requires the cli extra)')
    for command in (resolve, fetching, querying, *dataset_commands):
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
        elif args.command in DATASETS:
            if args.dataset_query == 'entities':
                module = query_module(args.command)
                datasets = module.entity_sources(
                    release, getattr(args, getattr(module, 'entity_type_filter', 'entity_type')),
                    observed_on=args.observed_on)
            else:
                datasets = query_sources(release, args.command,
                                         field=getattr(args, 'field', 'english')
                                         if args.dataset_query == 'search' else None,
                                         observed_on=args.observed_on,
                                         include_entity_name=getattr(args, 'include_entity_name', False))
            with connect(datasets, cache_dir=args.cache_dir) as connection:
                # DuckDB 2 relations are stateless and have no fetchmany().
                # Execute the bound relation once through this private CLI
                # connection so the existing output code can consume batches.
                _dataset_result(connection, args).create_view('_lgd_query_result')
                _query_output(connection.execute('SELECT * FROM _lgd_query_result'), args.format)
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
