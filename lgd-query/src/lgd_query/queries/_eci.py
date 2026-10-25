"""Reported LGD/ECI mappings from a caller-selected constituency report view."""

from ._common import code


LEVELS = ('parliament', 'assembly')
SOURCES = ('constituencies_mapping_pri', 'constituencies_mapping_urban')


def lookup(connection, source, *, level, constituency_code=None, state_code=None, eci_code=None):
    """Retain every distinct mapping; never select an arbitrary competing code.

    Ambiguity flags are calculated before filters, within the source view. The
    caller must supply a single observation, not a union of historical snapshots.
    Dates belong to the selected Dataset or historical view, not to ECI identity.
    """
    if source not in SOURCES:
        raise ValueError('Unsupported ECI mapping source')
    if level not in LEVELS:
        raise ValueError('level must be parliament or assembly')
    lgd, eci, name = (
        f'{level}_constituency{suffix}' for suffix in ('_code', '_eci_code', '_name')
    )
    conditions, params = [], []
    for column, value in (('state_code', state_code), (lgd, constituency_code), (eci, eci_code)):
        if value is not None:
            conditions.append(f'{column}=?')
            params.append(code(value))
    predicate = ' AND '.join(conditions) or 'true'
    return connection.sql(f'''WITH mappings AS (
        SELECT state_code,{lgd},{eci},
            coalesce(list(DISTINCT {name} ORDER BY {name})
                     FILTER(WHERE {name} IS NOT NULL AND trim({name})!=''),[]) AS lookup_names
        FROM {source}
        WHERE state_code IS NOT NULL AND trim(state_code) NOT IN ('','0')
          AND {lgd} IS NOT NULL AND trim({lgd}) NOT IN ('','0')
          AND {eci} IS NOT NULL AND trim({eci}) NOT IN ('','0')
        GROUP BY state_code,{lgd},{eci}
    ), marked AS (
        SELECT *,count(*) OVER(PARTITION BY state_code,{lgd})>1 AS conflicting_eci_codes,
                 count(*) OVER(PARTITION BY state_code,{eci})>1 AS eci_code_reused
        FROM mappings
    ) SELECT '{source}' AS source_dataset,* FROM marked WHERE {predicate}
      ORDER BY state_code,{lgd},{eci}''', params=params)
