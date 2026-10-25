"""Shared identifier validation and name matching for dataset SQL helpers."""

from typing import Literal

SearchMode = Literal['exact', 'prefix', 'contains', 'fuzzy']
DistanceMetric = Literal['levenshtein', 'damerau_levenshtein']


def code(value):
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not value or not value.isascii() or not value.isdigit():
        raise ValueError('code must be a nonnegative integer or a string of ASCII digits')
    # Preserve leading zeros and identifier namespaces. Never infer padding.
    return value


def census_year(year):
    if type(year) is not int or year not in (2001, 2011):
        raise ValueError('year must be 2001 or 2011')
    return year


def search(connection, name, *, table, alias, column, order, condition, filter_params,
           mode, max_distance, metric, limit, multiple_names=False):
    """Build a bound query using only SQL fragments supplied by our modules.

    Table, alias, column, order and condition are internal constants/allowlists;
    caller-supplied search text and filter values are always parameters.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError('name must be a nonempty string')
    if mode not in ('exact', 'prefix', 'contains', 'fuzzy'):
        raise ValueError('mode must be "exact", "prefix", "contains", or "fuzzy"')
    if metric not in ('levenshtein', 'damerau_levenshtein'):
        raise ValueError('metric must be "levenshtein" or "damerau_levenshtein"')
    if type(max_distance) is not int or max_distance < 0:
        raise ValueError('max_distance must be a nonnegative integer')
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError('limit must be a positive integer or None')
    normalized = f"NULLIF(lower(nfc_normalize(trim({alias}.{column}))), '')"
    if multiple_names:
        normalized = "NULLIF(lower(nfc_normalize(trim(candidate))), '')"
    needle = 'lower(nfc_normalize(trim(?)))'
    params = [name.strip()]
    selected = f'{alias}.*'
    if mode == 'fuzzy':
        distance = f'{metric}({normalized}, {needle})'
        if multiple_names:
            distance = f'list_min(list_transform({alias}.{column}, lambda candidate: {distance}))'
        selected += f', {distance} AS distance'
        match = 'distance <= ?'
        params.append(max_distance)
        order = 'distance, ' + order
    elif mode == 'exact':
        match = f'{normalized} = {needle}'
    else:
        function = 'starts_with' if mode == 'prefix' else 'contains'
        match = f'{function}({normalized}, {needle})'
    if multiple_names and mode != 'fuzzy':
        match = f'len(list_filter({alias}.{column}, lambda candidate: {match})) > 0'
    params.extend(filter_params)
    sql = (f'SELECT {selected} FROM {table} {alias} WHERE {match} AND {condition} '
           f'ORDER BY {order}')
    if limit is not None:
        sql += ' LIMIT ?'
        params.append(limit)
    return connection.sql(sql, params=params)
