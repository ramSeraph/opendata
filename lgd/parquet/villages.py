"""Canonicalize one village report; preserve each reported category."""

from .common import header_key, sql_identifier
from .csv_input import report
from .errors import InputRejected
from .schema import schema_id as field_schema_id, validate_fields


# These IDs describe our public schema, not CSV positions. Never recycle them.
FIELDS = (
    (1, 'village_code', 'VARCHAR', 'Village Code'),
    (2, 'village_version', 'INTEGER', 'Village Version'),
    (3, 'village_name', 'VARCHAR', 'Village Name (In English)'),
    (4, 'village_name_local', 'VARCHAR', 'Village Name (In Local)'),
    (5, 'village_status', 'VARCHAR', 'Village Status'),
    (6, 'village_category', 'VARCHAR', 'Village Category'),
    (7, 'remark', 'VARCHAR', 'Remark'),
    (8, 'state_code', 'VARCHAR', 'State Code'),
    (9, 'state_name', 'VARCHAR', 'State Name (In English)'),
    (10, 'district_code', 'VARCHAR', 'District Code'),
    (11, 'district_name', 'VARCHAR', 'District Name (In English)'),
    (12, 'subdistrict_code', 'VARCHAR', 'Sub-District Code'),
    (13, 'subdistrict_name', 'VARCHAR', 'Sub-District Name (In English)'),
    (14, 'village_census_2001_code', 'VARCHAR', 'Census 2001 Code'),
    (15, 'village_census_2011_code', 'VARCHAR', 'Census 2011 Code'),
)
OPTIONAL_FIELDS = {'village_name_local', 'village_status', 'village_category', 'remark'}
COLUMNS = [field[1] for field in FIELDS]
ATTRIBUTES = [column for column in COLUMNS if column != 'village_code']
validate_fields('villages', FIELDS)

ALIASES = {header_key(field[3]): field[1] for field in FIELDS}
ALIASES[header_key('Village Name (In Englsih)')] = 'village_name'


def source_schema(path):
    with report(path) as source:
        return source.headers, source.delimiter, *map_headers(source.headers)


def map_headers(headers):
    mapping = {}
    seen = set()
    for header in headers:
        key = header_key(header)
        if key in seen:
            raise ValueError(f'Duplicate source column: {header!r}')
        seen.add(key)
        if key == header_key('S.No.'):
            continue
        column = ALIASES.get(key)
        if column is None:
            raise ValueError(f'Unknown village column: {header!r}; add an explicit schema mapping')
        if column in mapping:
            raise ValueError(f'Multiple source columns map to {column}')
        mapping[column] = header
    missing = set(COLUMNS) - OPTIONAL_FIELDS - mapping.keys()
    if missing:
        raise ValueError(f'Missing required village columns: {sorted(missing)}')
    # Spelling/order changes do not change field availability or create row versions.
    schema_id = field_schema_id(mapping)
    return mapping, schema_id


def load_source(connection, path, *, headers=None, delimiter=None):
    with report(path, delimiter=delimiter) as source:
        if headers is not None and headers != source.headers:
            raise ValueError('Village CSV header changed while reading')
        headers = source.headers
        mapping, schema_id = map_headers(headers)
        source.load(connection, 'village_source')
    expressions = []
    for _, name, kind, _ in FIELDS:
        expression = sql_identifier(mapping[name]) if name in mapping else 'NULL'
        if kind == 'INTEGER':
            # Reject fractional/negative/overflowing versions rather than rounding them.
            invalid = connection.execute(f'''
                SELECT {expression} FROM village_source
                WHERE {expression} != '' AND
                    (NOT regexp_full_match({expression}, '[0-9]+')
                     OR try_cast({expression} AS INTEGER) IS NULL)
                LIMIT 1
            ''').fetchone()
            if invalid:
                raise ValueError(f'Invalid {name}: {invalid[0]!r}')
            expression = f'CAST(nullif({expression}, \'\') AS INTEGER)'
        else:
            expression = f'CAST({expression} AS VARCHAR)'
        expressions.append(f'{expression} AS {name}')
    connection.execute(f'''
        CREATE OR REPLACE TEMP TABLE village_incoming AS
        SELECT {', '.join(expressions)}, ?::VARCHAR AS source_schema_id
        FROM village_source
    ''', [schema_id])
    count = connection.execute('SELECT count(*) FROM village_incoming').fetchone()[0]
    if count == 0:
        raise ValueError('An empty national village export cannot establish completeness')
    invalid = connection.execute('''
        SELECT village_code, state_code FROM village_incoming
        WHERE NOT regexp_full_match(village_code, '[0-9]+')
           OR NOT regexp_full_match(state_code, '[0-9]+')
        LIMIT 1
    ''').fetchone()
    if invalid:
        raise ValueError(f'Invalid village/state identity: {invalid}')
    duplicate_codes = connection.execute('''
        SELECT village_code, village_category FROM village_incoming
        GROUP BY village_code, village_category HAVING count(*)>1
    ''').fetchall()
    if duplicate_codes:
        conflicts = connection.execute('''
            SELECT village_code, village_category FROM (
                SELECT DISTINCT * EXCLUDE (village_version) FROM village_incoming
            ) GROUP BY village_code, village_category HAVING count(*)>1 LIMIT 5
        ''').fetchall()
        if conflicts:
            raise InputRejected(f'Duplicate village versions have conflicting attributes: {conflicts}',
                                affected_keys=[dict(zip(('village_code', 'village_category'), row))
                                               for row in conflicts])
        unknown_versions = connection.execute('''
            SELECT n.village_code, n.village_category FROM village_incoming n
            WHERE n.village_version IS NULL AND EXISTS (
                SELECT 1 FROM village_incoming x WHERE x.village_code=n.village_code
                  AND x.village_category IS NOT DISTINCT FROM n.village_category
                GROUP BY x.village_code, x.village_category HAVING count(x.village_version)>0)
            LIMIT 5
        ''').fetchall()
        if unknown_versions:
            raise InputRejected(f'Cannot choose the highest unknown village version: {unknown_versions}',
                                affected_keys=[dict(zip(('village_code', 'village_category'), row))
                                               for row in unknown_versions])
        connection.execute('''
            CREATE OR REPLACE TEMP TABLE village_incoming AS
            SELECT * FROM village_incoming
            QUALIFY row_number() OVER (
                PARTITION BY village_code, village_category ORDER BY village_version DESC)=1
        ''')
        count = connection.execute('SELECT count(*) FROM village_incoming').fetchone()[0]
    return headers, mapping, schema_id, count
