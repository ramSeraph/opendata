"""Typed constituency identity, independent of a reported assembly's parent."""

DATASETS = ('constituency_coverage', 'constituencies_mapping_pri')
DERIVED = ('constituency_level', 'constituency_code')


def expressions(prefix=''):
    ac, pc = prefix+'assembly_constituency_code', prefix+'parliament_constituency_code'
    present = f"coalesce({ac},'') NOT IN ('','0')"
    return (f"CASE WHEN {present} THEN 'assembly' ELSE 'parliament' END AS constituency_level",
            f'CASE WHEN {present} THEN {ac} ELSE {pc} END AS constituency_code')


def add_identity(connection):
    connection.execute('CREATE OR REPLACE TEMP TABLE entity_incoming AS SELECT * REPLACE ('
                       + ','.join(expressions()) + ') FROM entity_incoming')


def normalize_pri_names(connection, keys):
    """Resolve only conflicting names, using one explicitly selected PRI view.

    No arbitrary label or future register is substituted when a reference is
    unavailable. Other attribute conflicts remain the parser's responsibility.
    """
    key_sql = ','.join(keys)
    connection.execute(f'''CREATE OR REPLACE TEMP TABLE pri_mapping_discrepancies AS
        SELECT DISTINCT * FROM entity_incoming
        QUALIFY count(DISTINCT local_body_name) OVER(PARTITION BY {key_sql})>1''')
    count = connection.execute('SELECT count(*) FROM pri_mapping_discrepancies').fetchone()[0]
    if not count:
        return 0
    available = connection.execute("""SELECT EXISTS(SELECT 1 FROM duckdb_views()
        WHERE view_name='pri_ward_reference') OR EXISTS(SELECT 1 FROM duckdb_tables()
        WHERE table_name='pri_ward_reference')""").fetchone()[0]
    if not available:
        raise ValueError('Conflicting PRI mapping names require a dated --pri-reference register')
    connection.execute('''CREATE OR REPLACE TEMP TABLE pri_mapping_names AS
        SELECT r.local_body_code,r.state_code,min(r.local_body_name) AS local_body_name
        FROM pri_ward_reference r WHERE EXISTS(SELECT 1 FROM pri_mapping_discrepancies d
            WHERE d.local_body_code=r.local_body_code AND d.state_code=r.state_code)
        GROUP BY r.local_body_code,r.state_code
        HAVING count(DISTINCT nullif(trim(r.local_body_name),''))=1
          AND count(*)=count(nullif(trim(r.local_body_name),''))''')
    missing = connection.execute('''SELECT DISTINCT d.local_body_code,d.state_code
        FROM pri_mapping_discrepancies d WHERE NOT EXISTS(SELECT 1 FROM pri_mapping_names r
            WHERE r.local_body_code=d.local_body_code AND r.state_code=d.state_code) LIMIT 5''').fetchall()
    if missing:
        raise ValueError(f'No unambiguous dated PRI body name for mapping conflicts: {missing}')
    join = ' AND '.join(f'd.{k} IS NOT DISTINCT FROM n.{k}' for k in keys)
    connection.execute(f'''UPDATE entity_incoming n SET local_body_name=r.local_body_name
        FROM pri_mapping_names r WHERE n.local_body_code=r.local_body_code AND n.state_code=r.state_code
          AND EXISTS(SELECT 1 FROM pri_mapping_discrepancies d WHERE {join})''')
    return count
