"""Command-line wrappers around the reader APIs and dataset queries."""

import argparse
import json
import math
import sys

from . import DEFAULT_METADATA_URL, connect, download, load_manifest, load_release
from .queries import districts as district_queries, states as state_queries
from .queries import subdistricts as subdistrict_queries
from .queries import DATASETS, get as query_module, prepare
from .queries._dataset import _date
from .queries._org_entities import RESOLUTION_STATUSES
from .queries._org_units import NAME_STATUSES


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


def _query_output(cursor, format, *, limit=None, columns=None, provenance=None):
    available = [column[0] for column in cursor.description]
    if columns:
        for column in columns:
            if available.count(column) != 1:
                raise ValueError(f'Unknown or ambiguous result column: {column!r}')
        indexes = [available.index(column) for column in columns]
    else:
        indexes = list(range(len(available)))
    columns = [available[i] for i in indexes]
    shown, truncated, printed = 0, False, False
    separator = ''
    if format == 'json':
        sys.stdout.write('{"columns": ' + json.dumps(columns, ensure_ascii=False) + ', "rows": [')
    while True:
        size = 1000 if limit is None else min(1000, limit - shown + 1)
        batch = cursor.fetchmany(size)
        if not batch:
            break
        if limit is not None and len(batch) > limit - shown:
            batch = batch[:limit - shown]
            truncated = True
        rows = [tuple(row[i] for i in indexes) for row in batch]
        shown += len(rows)
        if rows:
            printed = True
            if format == 'table':
                _table(columns, rows)
            else:
                for row in rows:
                    sys.stdout.write(separator + json.dumps(_json_value(row), ensure_ascii=False,
                                                           default=str, allow_nan=False))
                    separator = ',\n'
        if truncated:
            break
    if format == 'table':
        if not printed:
            _table(columns, [])
        if truncated:
            print(f'Showing the first {limit} rows; more matches exist. Use --all or raise --limit.')
    else:
        sys.stdout.write(']')
        if limit is not None:
            sys.stdout.write(', "truncated": ' + json.dumps(truncated) + ', "limit": ' + str(limit))
        if provenance is not None:
            sys.stdout.write(', "provenance": ' + json.dumps(provenance, ensure_ascii=False, default=str))
        sys.stdout.write('}\n')


def _positive(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('limit must be a positive integer') from error
    if number < 1:
        raise argparse.ArgumentTypeError('limit must be a positive integer')
    return number


def _output_options(command, *, preview):
    limits = command.add_mutually_exclusive_group()
    limits.add_argument('--limit', type=_positive, default=20 if preview else None,
                        help='Maximum displayed rows (default: 20)' if preview else 'Maximum displayed rows')
    limits.add_argument('--all', dest='show_all', action='store_true', help='Return every matching row')
    command.add_argument('--columns', nargs='+', help='Result columns to display, in this order')
    command.add_argument('--provenance', action='store_true', help='Include generation and source details in JSON')
    if preview:
        command.add_argument('--is-null', action='append', metavar='COLUMN', help='Require SQL NULL; repeat for multiple columns')
        command.add_argument('--is-blank', action='append', metavar='COLUMN', help='Require the exact empty string; repeat for multiple columns')


def _provenance(release, datasets):
    return dict(generation=release.generation, immutable_url=release.immutable_url,
                sources=[dict(dataset=d.name, observed_on=d.observed_on, status=d.status,
                              reason=d.reason, representation=d.representation,
                              uploaded_at=d.uploaded_at, coverage=d.coverage,
                              url=d.parquet.url, sha256=d.parquet.sha256) for d in datasets])


def _show_sources(release, datasets):
    _table(['Dataset', 'Observed on', 'Status', 'Reason'],
           [(d.name, d.observed_on if d.observed_on else 'Event report', d.status, d.reason)
            for d in datasets], title=f'Sources · {release.generation}')


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


def _dataset_plan(args):
    module = query_module(args.command)
    action = args.dataset_query
    missing = {name: getattr(args, name) for name in ('is_null', 'is_blank')
               if getattr(args, name) is not None}
    if action == 'eci-codes':
        if missing:
            raise ValueError('ECI lookups exclude missing identifiers; use list for missing-value filters')
        return prepare(args.command, 'eci_codes', level=args.level,
                       constituency_code=args.constituency_code, state_code=args.state_code,
                       eci_code=args.eci_code)
    if args.command in _DATASET_QUERIES:
        filters = dict(missing)
        if action != 'code':
            for name in ('kind', 'state_code', 'district_code'):
                if getattr(args, name, None) is not None:
                    filters[name] = getattr(args, name)
        lookup_code = getattr(args, 'code', None)
    else:
        filters = {key: getattr(args, key, None) for key in module.filters
                   if getattr(args, key, None) is not None}
        filters.update(missing)
        if getattr(args, 'include_entity_name', False):
            filters['include_entity_name'] = True
        for key in ('entity_name_status', 'resolution_status'):
            if getattr(args, key, None) is not None:
                filters[key] = getattr(args, key)
        if args.command in ('state_org_units', 'central_org_units') and getattr(args, 'entity_name', None) is not None:
            filters['entity_name'] = args.entity_name
        lookup_code = getattr(args, 'lookup_code', None)
    if action in ('code', 'id'):
        return prepare(args.command, 'by_id' if action == 'id' else 'by_code', lookup_code, **filters)
    if action == 'census-code':
        return prepare(args.command, 'by_census_code', lookup_code, year=args.year, **filters)
    if action in ('list', 'entities', 'references', 'types'):
        return prepare(args.command, 'reference_types' if action == 'types' else action, **filters)
    if hasattr(args, 'field'):
        filters['field'] = args.field
    # One additional match establishes truncation without computing a count.
    return prepare(args.command, 'search', args.name, mode=args.mode,
                   max_distance=args.max_distance, metric=args.metric,
                   limit=None if args.limit is None else args.limit + 1, **filters)


def _filter_help(dataset, column):
    organization = '_org' in dataset or '_admin_dept' in dataset or dataset.startswith('org_unit_')
    if organization:
        meanings = {
            'state_code': 'Organization report state; 0 means central scope in combined reports. Not the target geographic state',
            'state_name': 'Reported organization-scope state name; not a target-state filter',
            'organization_code': 'LGD organization code; distinct from an office/unit code',
            'organization_unit_code': 'LGD office/unit code',
            'organization_unit_specific_code': 'Organization-defined text identifier; not a universal LGD code or PIN',
            'entity_type': 'Signed location type: 1–5 geography, -1 through -8 bodies, >5 custom levels. See types',
            'entity_code': 'Office location code; interpreted with its entity type',
            'entity_name': 'Reported office-location label; distinct from geographic coverage',
            'covered_entity_type': 'Exact coverage-target type, e.g. Subdistrict or Village; see types',
            'covered_entity_code': 'Coverage target code in the covered-entity type namespace',
            'coverage_details_reported': 'Source text true/false; false means details not supplied, not zero coverage',
            'coverage_type': 'Reported coverage claim: F full or P partial',
            'organization_level_code': "Office's own organizational level code",
            'report_organization_level_code': "Selected report level; may differ from a returned office's own level",
            'report_organization_level_name': 'Selected report level label; descendants can appear in the same selection',
            'administrative_unit_level_code': 'Custom administrative-level definition; not an office identifier',
            'administrative_unit_code': 'Member of an administrative level; distinct from an organization-unit code',
            'designation_code': 'Designation/title identifier; does not identify a person or assign an office',
        }
        if column in meanings:
            return meanings[column]
    return f'Exact {column} filter' if column not in ('since', 'until') else 'Inclusive event date (YYYY-MM-DD)'


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
    parsers = [listing, lookup, search]
    entities = None
    if hasattr(module, 'entities'):
        entities = actions.add_parser('entities', help='Follow typed entity codes to their register records',
            description='Filters select source offices/claims; output contains matched register records. '
                        'Use references to retain office links and unresolved organization references.'
                        if hasattr(module, 'references') else None)
        parsers.append(entities)
    if hasattr(module, 'references'):
        references = actions.add_parser('references', help='Resolve references while retaining source offices/claims',
            description='Filters select source rows. Output uses source_ and target_ column prefixes. '
                        'Unresolved and no-details rows remain visible. Select a type to load fewer registers.')
        references.add_argument('--resolution-status', choices=RESOLUTION_STATUSES,
                                help='Select a resolution outcome after matching')
        types = actions.add_parser('types', help='Summarize observed reference types and labels',
            description='Reads only this source report. Lists observed types, labels, counts and known target registers; '
                        'resolvable means a namespace is known, not that every reference matches.')
        parsers.extend((references, types))
    if module.census_years:
        census = actions.add_parser('census-code', help='Look up the primary entity in one census namespace')
        census.add_argument('lookup_code')
        census.add_argument('--year', type=int, choices=module.census_years, required=True)
        parsers.append(census)
    for command in parsers:
        if dataset in ('state_org_units', 'central_org_units') and command in (listing, lookup, search):
            command.add_argument('--include-entity-name', action='store_true',
                                 help='Resolve location labels from org_unit_details')
            command.add_argument('--entity-name', help='Exact unambiguous details label; enables name enrichment')
            command.add_argument('--entity-name-status', choices=NAME_STATUSES,
                                 help='Select missing, matched or ambiguous details labels; enables enrichment')
        for column in module.filters:
            if command is lookup and column == spec.primary_code:
                continue
            if command is entities and column == getattr(module, 'entity_type_filter', 'entity_type'):
                command.add_argument('--'+column.replace('_', '-'),
                                     choices=getattr(module, 'entity_types', None), required=True,
                                     help=_filter_help(dataset, column))
                continue
            command.add_argument('--'+column.replace('_', '-'), dest=column,
                                 type=int if column in spec.integers else str,
                                 help=_filter_help(dataset, column))
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
    for command in dataset_commands:
        _output_options(command, preview=True)
    _output_options(querying, preview=False)
    args = parser.parse_args(argv)
    try:
        if getattr(args, 'observed_on', None) is not None:
            args.observed_on = _date(args.observed_on).isoformat()
        if getattr(args, 'show_all', False):
            args.limit = None
        selected_columns = getattr(args, 'columns', None)
        if selected_columns and (any(not c for c in selected_columns) or
                                 len(set(selected_columns)) != len(selected_columns)):
            raise ValueError('--columns requires nonempty, distinct column names')
        plan = _dataset_plan(args) if args.command in DATASETS else None
        if plan and selected_columns:
            unknown = set(selected_columns) - set(plan.columns)
            if unknown:
                raise ValueError(f'Unknown result column(s): {", ".join(sorted(unknown))}')
        params = None
        if args.command == 'query' and args.params is not None:
            params = json.loads(args.params)
            if not isinstance(params, (list, dict)):
                raise ValueError('--params must be a JSON array or object')
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
            datasets = plan.sources(release, observed_on=args.observed_on)
            with connect(datasets, cache_dir=args.cache_dir) as connection:
                result = plan.execute(connection)
                if args.columns:
                    # Names were checked against the prepared result schema.
                    result = result.project(', '.join('"' + c.replace('"', '""') + '"' for c in args.columns))
                if args.limit is not None:
                    result = result.limit(args.limit + 1)
                result.create_view('_lgd_query_result')
                cursor = connection.execute('SELECT * FROM _lgd_query_result')
                if args.format == 'table':
                    _show_sources(release, datasets)
                _query_output(cursor, args.format, limit=args.limit,
                              provenance=_provenance(release, datasets) if args.provenance else None)
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
                with connect(datasets, cache_dir=args.cache_dir) as connection:
                    cursor = connection.execute(args.sql, params)
                    if args.format == 'table':
                        _show_sources(release, datasets)
                    _query_output(cursor, args.format, limit=args.limit, columns=args.columns,
                                  provenance=_provenance(release, datasets) if args.provenance else None)
    except Exception as error:
        parser.exit(1, f'lgd-query: {error}\n')
    return 0
