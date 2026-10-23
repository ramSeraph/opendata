"""Canonicalize cumulative event reports, preserving every reported row."""

from .common import header_key, sql_identifier, sql_string
from .csv_input import report
from .schema import validate_fields


# IDs are stable public field identities, independent of source column order.
SCHEMAS = {
    'changes': (
        (1, 'report_serial', 'VARCHAR', 'S.No.'),
        (2, 'entity_type', 'VARCHAR', 'Entity Type'),
        (3, 'entity_code', 'VARCHAR', 'Entity Code'),
        (4, 'entity_version', 'INTEGER', 'Entity Version'),
        (5, 'entity_name', 'VARCHAR', 'Entity Name (In English)'),
        (6, 'entity_name_local', 'VARCHAR', 'Entity Name (In Local)'),
        (7, 'census_code', 'VARCHAR', 'Census Code'),
        (8, 'operation_name', 'VARCHAR', 'Operation'),
        (9, 'report_date', 'DATE', 'date'),
    ),
    'transactions': (
        (1, 'transaction_id', 'VARCHAR', 'Transaction ID'),
        (2, 'operation_code', 'VARCHAR', 'Operation Code'),
        (3, 'operation_name', 'VARCHAR', 'Operation Name'),
        (4, 'description', 'VARCHAR', 'Description'),
        (5, 'transaction_date', 'DATE', 'Transaction Date'),
        (6, 'state_code', 'VARCHAR', 'State Code'),
        (7, 'state_name', 'VARCHAR', 'State Name'),
    ),
}
DATE_FIELDS = {'changes': 'report_date', 'transactions': 'transaction_date'}
for dataset, fields in SCHEMAS.items():
    validate_fields(dataset, fields)
DATE_FORMATS = {'changes': '%d-%m-%Y', 'transactions': '%d-%b-%Y'}


def load_csv(connection, dataset, path):
    with report(path, delimiter=',') as source:
        headers = source.headers
        aliases = {header_key(h): n for _, n, _, h in SCHEMAS[dataset]}
        mapping = {}
        for h in headers:
            name = aliases.get(header_key(h))
            if name is None or name in mapping:
                raise ValueError(f'Unknown or duplicate {dataset} column: {h!r}')
            mapping[name] = h
        if set(mapping) != set(aliases.values()):
            raise ValueError(f'Missing {dataset} columns: {sorted(set(aliases.values())-set(mapping))}')
        source.load(connection, 'raw_events')
    source_count = connection.execute('SELECT count(*) FROM raw_events').fetchone()[0]
    if not source_count:
        raise ValueError('Empty cumulative event report requires review')
    expressions = []
    for _, name, kind, _ in SCHEMAS[dataset]:
        source = sql_identifier(mapping[name])
        expression = source
        if kind == 'DATE':
            fmt = sql_string(DATE_FORMATS[dataset])
            expression = f'CAST(try_strptime({source}, {fmt}) AS DATE)'
            invalid = f'{expression} IS NULL OR strftime({expression}, {fmt})!={source}'
        elif kind == 'INTEGER':
            expression = f'try_cast({source} AS INTEGER)'
            invalid = f'{expression} IS NULL OR cast({expression} AS VARCHAR)!={source} OR {expression}<0'
        elif (name.endswith('_code') and name != 'census_code') or name == 'transaction_id':
            invalid = f"NOT regexp_full_match({source}, '[0-9]+')"
        elif name == 'report_serial':
            invalid = f"NOT regexp_full_match({source}, '[0-9]+|[1-9][0-9]{{0,2}}(,[0-9]{{3}})+')"
        else:
            invalid = 'false'
        if connection.execute(f'SELECT count(*) FROM raw_events WHERE {invalid}').fetchone()[0]:
            raise ValueError(f'Invalid or non-lossless {name} conversion')
        expressions.append(f'{expression} AS {name}')
    connection.execute('CREATE TEMP TABLE event_rows AS SELECT ' + ', '.join(expressions) + ' FROM raw_events')
    connection.execute('DROP TABLE raw_events')
    return headers, source_count
