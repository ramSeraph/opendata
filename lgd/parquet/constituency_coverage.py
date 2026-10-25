"""One coded association, with an unresolved value for contradictory flags.

The source accepts exactly two coverage values. NULL in a normalized row means
both were reported, so the original distinct claims remain reconstructible.
Other attribute conflicts still require review; this does not adjudicate them.
"""

def normalize(connection, keys):
    key_sql = ', '.join(keys)
    connection.execute(f'''CREATE OR REPLACE TEMP TABLE constituency_coverage_discrepancies AS
        SELECT DISTINCT * FROM entity_incoming
        QUALIFY count(DISTINCT coverage_type) OVER (PARTITION BY {key_sql})>1''')
    connection.execute(f'''CREATE OR REPLACE TEMP TABLE entity_incoming AS
        SELECT DISTINCT * REPLACE (
            CASE WHEN count(DISTINCT coverage_type) OVER (PARTITION BY {key_sql})>1
                 THEN NULL::VARCHAR ELSE coverage_type END AS coverage_type)
        FROM entity_incoming''')
    return connection.execute('SELECT count(*) FROM entity_incoming WHERE coverage_type IS NULL').fetchone()[0]
