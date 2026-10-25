"""Read organization coverage by unit, target type and target code."""

from .common import header_key, sql_identifier
from .csv_input import report
from .keys import ROW_KEYS
from .schema import schema_id, validate_fields


FIELDS = (
    (1, 'organization_unit_code', 'VARCHAR', 'Org Unit Code'),
    (2, 'organization_unit_name', 'VARCHAR', 'Org Unit Name (In English)'),
    (3, 'entity_code', 'VARCHAR', 'Entity Code'),
    (4, 'entity_name', 'VARCHAR', 'Entity Name'),
    (5, 'organization_unit_specific_code', 'VARCHAR', 'Org Specific Code'),
    (6, 'covered_entity_code', 'VARCHAR', 'Covered Entity Code'),
    (7, 'covered_entity_name', 'VARCHAR', 'Covered Entity Name'),
    (8, 'covered_entity_type', 'VARCHAR', 'Covered Entity Type'),
    (9, 'coverage_type', 'VARCHAR', 'Coverage Type'),
    (10, 'coverage_details_reported', 'VARCHAR', 'Coverage Details Reported'),
    (11, 'report_organization_level_code', 'VARCHAR', 'Report Org Located Level Code'),
    (12, 'report_organization_level_name', 'VARCHAR', 'Report Org Level Specific Name'),
    (13, 'organization_code', 'VARCHAR', 'Base Organization Code'),
    (14, 'organization_name', 'VARCHAR', 'Base Organization Name'),
    (15, 'state_code', 'VARCHAR', 'State Code'),
    (16, 'state_name', 'VARCHAR', 'State Name'),
)
validate_fields('org_unit_coverage', FIELDS)
KEY_COLUMNS = ROW_KEYS['org_unit_coverage']


def load_source(connection, path):
    with report(path, delimiter=',') as source:
        headers = source.headers
        aliases = {header_key(header): name for _, name, _, header in FIELDS}
        mapping = {}
        for header in headers:
            name = aliases.get(header_key(header))
            if name is None or name in mapping:
                raise ValueError(f'Unknown or duplicate org_unit_coverage column: {header!r}')
            mapping[name] = header
        missing = set(aliases.values()) - mapping.keys()
        if missing:
            raise ValueError(f'Missing org_unit_coverage columns: {sorted(missing)}')
        source.load(connection, 'organization_coverage_source')
    projection = ', '.join(f'{sql_identifier(mapping[n])} AS {n}' for _, n, _, _ in FIELDS)
    connection.execute(f'''CREATE OR REPLACE TEMP TABLE organization_coverage_incoming AS
        SELECT {projection} FROM organization_coverage_source''')
    connection.execute('DROP TABLE organization_coverage_source')
    count = connection.execute('SELECT count(*) FROM organization_coverage_incoming').fetchone()[0]
    if not count:
        raise ValueError('Empty organization coverage report requires review')
    codes = ('organization_unit_code', 'organization_code', 'state_code', 'report_organization_level_code')
    invalid_codes = ' OR '.join(f"NOT regexp_full_match({name}, '[0-9]+')" for name in codes)
    # Keep signed location sentinels compatible with other organization reports.
    invalid_codes += " OR NOT regexp_full_match(entity_code, '-?[0-9]+')"
    invalid = connection.execute(f'''SELECT organization_unit_code, organization_code, state_code,
            report_organization_level_code, entity_code FROM organization_coverage_incoming
            WHERE {invalid_codes} LIMIT 5''').fetchall()
    if invalid:
        raise ValueError(f'Invalid organization coverage identity: {invalid}')
    invalid = connection.execute('''SELECT organization_unit_code, covered_entity_code,
            covered_entity_type, coverage_type, coverage_details_reported
        FROM organization_coverage_incoming WHERE
            coverage_details_reported NOT IN ('true', 'false')
            OR (coverage_details_reported='false' AND
                (covered_entity_code!='' OR covered_entity_name!=''
                 OR covered_entity_type!='' OR coverage_type!=''))
            OR (coverage_details_reported='true' AND
                (NOT regexp_full_match(covered_entity_code, '[0-9]+')
                 OR coverage_type NOT IN ('F', 'P')))
        LIMIT 5''').fetchall()
    if invalid:
        raise ValueError(f'Invalid organization coverage claim/placeholder: {invalid}')
    source_count = count
    keys = ', '.join(KEY_COLUMNS)
    repeated = connection.execute(f'''SELECT EXISTS (
        SELECT {keys} FROM organization_coverage_incoming GROUP BY {keys}
        HAVING count(*)>1)''').fetchone()[0]
    if repeated:
        # Exact copies are redundant. Different labels, flags or request context
        # for one association require review instead of an arbitrary winner.
        connection.execute('''CREATE OR REPLACE TEMP TABLE organization_coverage_incoming AS
            SELECT DISTINCT * FROM organization_coverage_incoming''')
        conflicts = connection.execute(f'''SELECT {keys} FROM organization_coverage_incoming
            GROUP BY {keys} HAVING count(*)>1 LIMIT 5''').fetchall()
        if conflicts:
            raise ValueError(f'Organization coverage has conflicting attributes for unit/type/target key: {conflicts}')
        count = connection.execute('SELECT count(*) FROM organization_coverage_incoming').fetchone()[0]
    return headers, mapping, schema_id(mapping), count, source_count
