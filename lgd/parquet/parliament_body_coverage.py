"""Retain blank coverage; represent simultaneous F/P claims as unresolved NULL."""

from .constituency_coverage import normalize as normalize_flags


def normalize(connection, keys):
    invalid = connection.execute("""SELECT coverage_type FROM entity_incoming
        WHERE coverage_type IS NULL OR coverage_type NOT IN ('','F','P') LIMIT 1""").fetchone()
    if invalid:
        raise ValueError(f'Unrecognized parliamentary/body coverage: {invalid}')
    conflict = connection.execute(f'''SELECT {','.join(keys)} FROM entity_incoming
        GROUP BY {','.join(keys)} HAVING bool_or(coverage_type='')
            AND count(DISTINCT coverage_type)>1 LIMIT 1''').fetchone()
    if conflict:
        raise ValueError(f'Blank coverage conflicts with a supplied flag: {conflict}')
    return normalize_flags(connection, keys)
