"""Reconcile conflicting PRI ward rows using a dated body-register snapshot.

The caller supplies ``pri_ward_reference`` with the PRI body schema and pins
its provenance. This module does not fetch data or read history. Unresolved
ward updates are withheld, never guessed; history may carry an older resolved
row. Original conflicting rows remain in ``pri_ward_discrepancies``.
"""

from .errors import InputRejected
from .pri_ward_exclusions import FIRST, UNTIL, WARD_BODY_PAIRS


CORE = ('ward_number', 'ward_name', 'ward_name_local', 'local_body_code')
LABELS = ('local_body_name', 'local_body_type_name', 'state_code', 'state_name',
          'district_panchayat_name', 'intermediate_panchayat_name')


def exclude_reviewed(connection, *, observed_on=None):
    """Remove only reviewed ward/body/date assertions and retain their values."""
    c = connection
    c.execute('''CREATE OR REPLACE TEMP TABLE pri_ward_excluded_pairs AS
        SELECT unnest(?::STRUCT(ward_code VARCHAR,local_body_code VARCHAR)[],recursive:=true)''',
        [[dict(ward_code=ward,local_body_code=body) for ward,body in WARD_BODY_PAIRS]])
    matched = '''EXISTS (SELECT 1 FROM pri_ward_excluded_pairs x
        WHERE x.ward_code=e.ward_code AND x.local_body_code=e.local_body_code)'''
    if observed_on is None and c.execute(f'SELECT EXISTS (SELECT 1 FROM entity_incoming e WHERE {matched})').fetchone()[0]:
        raise ValueError('PRI ward observation date is required for reviewed exclusions')
    active = observed_on is not None and FIRST <= observed_on < UNTIL
    c.execute(f'''CREATE OR REPLACE TEMP TABLE pri_ward_ignored AS
        SELECT DISTINCT e.* FROM entity_incoming e WHERE {matched if active else 'false'}''')
    ignored = c.execute('SELECT count(*) FROM pri_ward_ignored').fetchone()[0]
    if ignored:
        c.execute(f'DELETE FROM entity_incoming e WHERE {matched}')
    return dict(ignored_source_rows=ignored,
        ignored_wards=c.execute('SELECT count(DISTINCT ward_code) FROM pri_ward_ignored').fetchone()[0])


def resolve(connection, columns, *, reference_available=False, observed_on=None):
    """Apply reviewed exclusions, reconcile variants, and preserve evidence."""
    c = connection
    ignored_info = exclude_reviewed(c, observed_on=observed_on)
    ignored = ignored_info['ignored_source_rows']
    result = _resolve_conflicts(c, columns, reference_available=reference_available)
    if ignored:
        exists = c.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name='pri_ward_discrepancies'").fetchone()[0]
        query = f'''SELECT *, 'ignored' AS resolution, []::VARCHAR[] AS unresolved_fields,
            {', '.join('NULL::VARCHAR AS resolved_'+col for col in LABELS)} FROM pri_ward_ignored'''
        if exists:
            c.execute('INSERT INTO pri_ward_discrepancies BY NAME '+query)
        else:
            c.execute('CREATE TEMP TABLE pri_ward_discrepancies AS '+query)
    return result | ignored_info


def _resolve_conflicts(connection, columns, *, reference_available=False):
    """Normalize ``entity_incoming`` to one row per ward; return accounting.

    A missing reference *input* is an error when conflicting rows need it.
    Missing codes inside a supplied register are unresolved source updates.
    Names/state are resolved only where source variants disagree; undisputed
    values remain supplied values. State code and name are resolved together.
    """
    c = connection
    c.execute('DROP TABLE IF EXISTS pri_ward_discrepancies')
    c.execute('''CREATE OR REPLACE TEMP TABLE pri_ward_duplicate_codes AS
        SELECT ward_code FROM entity_incoming GROUP BY ward_code HAVING count(*)>1''')
    if not c.execute('SELECT EXISTS (SELECT 1 FROM pri_ward_duplicate_codes)').fetchone()[0]:
        return dict(conflicting_wards=0, resolved_wards=0, unresolved_wards=0,
                    unresolved_source_rows=0, unresolved_ward_codes=[])
    c.execute('''CREATE OR REPLACE TEMP TABLE pri_ward_variants AS
        SELECT DISTINCT * FROM entity_incoming
        WHERE ward_code IN (SELECT ward_code FROM pri_ward_duplicate_codes)''')
    attrs = [column for column in columns if column != 'ward_code'] + ['source_schema_id']
    distinct = lambda col: f'(count(DISTINCT {col}) + CASE WHEN bool_or({col} IS NULL) THEN 1 ELSE 0 END)'
    aggregates = ', '.join(f'any_value({col}) AS {col}, {distinct(col)} AS variants_{col}' for col in attrs)
    c.execute(f'''CREATE OR REPLACE TEMP TABLE pri_ward_groups AS
        SELECT ward_code,count(*) AS variant_count,{aggregates}
        FROM pri_ward_variants GROUP BY ward_code''')
    invalid = c.execute('SELECT ward_code FROM pri_ward_groups WHERE ' +
                        ' OR '.join(f'variants_{col}>1' for col in (*CORE, 'source_schema_id')) + ' LIMIT 5').fetchall()
    if invalid:
        raise InputRejected('PRI ward codes have conflicting ward attributes or body codes: '
                            f'{invalid}', affected_keys=[{'ward_code': r[0]} for r in invalid])
    conflicts = c.execute('SELECT count(*) FROM pri_ward_groups WHERE variant_count>1').fetchone()[0]
    if conflicts and not reference_available:
        raise ValueError('Conflicting PRI wards require a dated PRI local-body reference')
    if not conflicts:
        c.execute('''CREATE OR REPLACE TEMP TABLE entity_incoming AS
            SELECT * FROM entity_incoming WHERE ward_code NOT IN (SELECT ward_code FROM pri_ward_duplicate_codes)
            UNION ALL SELECT * FROM pri_ward_variants''')
        return dict(conflicting_wards=0, resolved_wards=0, unresolved_wards=0,
                    unresolved_source_rows=0, unresolved_ward_codes=[])
    ambiguous = c.execute('''SELECT local_body_code FROM pri_ward_reference
        GROUP BY local_body_code HAVING count(*)>1 LIMIT 5''').fetchall()
    if ambiguous:
        raise ValueError(f'PRI reference is not unique by local-body code: {ambiguous}')
    # Codes identify bodies nationally. A bad source state must not prevent
    # looking up the same body in its actual reported state.
    present = lambda value: f"CASE WHEN nullif(trim({value}),'') IS NOT NULL THEN {value} END"
    resolved = {
        'local_body_name': present('b.local_body_name'),
        'local_body_type_name': present('b.local_body_type_name'),
        'state_code': "nullif(b.state_code,'')",
        'state_name': present('b.state_name'),
        'district_panchayat_name': f"""CASE
            WHEN b.local_body_type_code='1' THEN ''
            WHEN b.local_body_type_code IN ('2','3') AND p.local_body_type_code='1'
                THEN {present('p.local_body_name')}
            WHEN b.local_body_type_code='3' AND p.local_body_type_code='2'
                AND gp.local_body_type_code='1' THEN {present('gp.local_body_name')} END""",
        'intermediate_panchayat_name': f"""CASE
            WHEN b.local_body_type_code IN ('1','2') THEN ''
            WHEN b.local_body_type_code='3' AND p.local_body_type_code='1' THEN ''
            WHEN b.local_body_type_code='3' AND p.local_body_type_code='2'
                THEN {present('p.local_body_name')} END""",
    }
    needs = {col: ('g.variants_state_code>1 OR g.variants_state_name>1'
                   if col in ('state_code', 'state_name') else f'g.variants_{col}>1')
             for col in LABELS}
    selections = [f'CASE WHEN {needs[col]} THEN {expr} ELSE g.{col} END AS {col}'
                  for col, expr in resolved.items()]
    unresolved = ', '.join(f"CASE WHEN ({needs[col]}) AND ({expr}) IS NULL THEN '{col}' END"
                           for col, expr in resolved.items())
    c.execute(f'''CREATE OR REPLACE TEMP TABLE pri_ward_selected AS
        SELECT g.* EXCLUDE ({', '.join(LABELS)}), {', '.join(selections)},
            list_filter([{unresolved}], lambda field: field IS NOT NULL) AS unresolved_fields
        FROM pri_ward_groups g LEFT JOIN pri_ward_reference b USING(local_body_code)
        LEFT JOIN pri_ward_reference p ON p.local_body_code=b.parent_local_body_code
            AND p.state_code=b.state_code AND p.local_body_code!=b.local_body_code
        LEFT JOIN pri_ward_reference gp ON gp.local_body_code=p.parent_local_body_code
            AND gp.state_code=b.state_code AND gp.local_body_code NOT IN (b.local_body_code,p.local_body_code)''')
    c.execute(f'''CREATE TEMP TABLE pri_ward_discrepancies AS
        SELECT v.*, CASE WHEN len(s.unresolved_fields)>0 THEN 'not_updated' ELSE 'resolved' END AS resolution,
            s.unresolved_fields, {', '.join('s.'+col+' AS resolved_'+col for col in LABELS)}
        FROM pri_ward_variants v JOIN pri_ward_selected s USING(ward_code)
        WHERE s.variant_count>1''')
    codes = [r[0] for r in c.execute('SELECT ward_code FROM pri_ward_selected '
                                    'WHERE len(unresolved_fields)>0 ORDER BY ward_code').fetchall()]
    withheld = c.execute('''SELECT count(*) FROM entity_incoming WHERE ward_code IN
        (SELECT ward_code FROM pri_ward_selected WHERE len(unresolved_fields)>0)''').fetchone()[0]
    c.execute(f'''CREATE OR REPLACE TEMP TABLE entity_incoming AS
        SELECT * FROM entity_incoming WHERE ward_code NOT IN (SELECT ward_code FROM pri_ward_duplicate_codes)
        UNION ALL SELECT {', '.join(columns)}, source_schema_id
        FROM pri_ward_selected WHERE len(unresolved_fields)=0''')
    return dict(conflicting_wards=conflicts, resolved_wards=conflicts-len(codes),
                unresolved_wards=len(codes), unresolved_source_rows=withheld,
                unresolved_ward_codes=codes)
