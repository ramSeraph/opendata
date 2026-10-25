"""Queries for the states report, which includes states and union territories.

Every helper needs only the ``states`` view created by lgd_query.connect().
Results retain all supplied columns and names. Empty matches return an empty
relation. Consume results while the caller's connection remains open.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ._missing import Columns, missing_conditions
from ._common import DistanceMetric, SearchMode, census_year, code as _code, search as _search

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection, DuckDBPyRelation


Kind = Literal['state', 'ut']
NameField = Literal['english', 'local']

columns = ('state_code', 'state_version', 'state_name', 'state_name_local', 'state_census_2001_code', 'state_census_2011_code', 'state_or_ut')


def _missing(condition, is_null, is_blank):
    return " AND ".join([condition, *missing_conditions(columns, alias='s',
        nontext=('state_version',), is_null=is_null, is_blank=is_blank)])


_ORDER = 'lower(nfc_normalize(trim(s.state_name))), s.state_code'


def _kind(kind):
    if kind is None:
        return 'TRUE', []
    if kind not in ('state', 'ut'):
        raise ValueError('kind must be "state", "ut", or None')
    return 's.state_or_ut = ?', ['S' if kind == 'state' else 'U']


def list(connection: DuckDBPyConnection, *, kind: Kind | None = None,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """List all reported states/UTs, optionally filtering their classification.

    ``kind='state'`` selects supplied ``state_or_ut='S'``; ``'ut'`` selects
    ``'U'``. None retains every row, including missing/unknown classifications.
    Results are ordered by English name, then LGD code.
    """
    condition, params = _kind(kind)
    condition = _missing(condition, is_null, is_blank)
    return connection.sql(f'SELECT s.* FROM states s WHERE {condition} ORDER BY {_ORDER}', params=params)


def by_code(connection: DuckDBPyConnection, code: str | int, *,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Look up an LGD state code, preserving string codes exactly."""
    return connection.sql('SELECT s.* FROM states s WHERE s.state_code = ? '
                          f'AND {_missing("TRUE", is_null, is_blank)} ORDER BY {_ORDER}', params=[_code(code)])


def by_census_code(connection: DuckDBPyConnection, code: str | int, *,
                   year: Literal[2001, 2011],
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Look up a census identifier in its explicitly selected year's namespace.

    No zero padding is inferred. Use a string to retain leading zeros. All
    matches are returned; this helper does not assume census codes are unique.
    """
    year = census_year(year)
    return connection.sql(f'SELECT s.* FROM states s WHERE s.state_census_{year}_code = ? '
                          f'AND {_missing("TRUE", is_null, is_blank)} ORDER BY {_ORDER}', params=[_code(code)])


def search(connection: DuckDBPyConnection, name: str, *, mode: SearchMode = 'contains',
           field: NameField = 'english', kind: Kind | None = None,
           max_distance: int = 2, metric: DistanceMetric = 'levenshtein',
           limit: int | None = 20,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Search English or supplied local names without changing returned text.

    Comparisons use trimmed, NFC-normalized, lowercase strings. Prefix and
    contains searches are literal: '%' and '_' are not wildcards. Missing/blank
    local names do not match and are not replaced with the English name.

    Fuzzy mode adds ``distance`` and returns only distances <= max_distance,
    ordered by distance, English name and code. It uses DuckDB's built-in edit
    distance functions, which count UTF-8 bytes for non-ASCII text; these scores
    are not Unicode character/grapheme distances or transliteration matches.
    max_distance/metric apply only in fuzzy mode. None disables the result limit.
    """
    if field not in ('english', 'local'):
        raise ValueError('field must be "english" or "local"')
    classification, kind_params = _kind(kind)
    classification = _missing(classification, is_null, is_blank)
    column = 'state_name' if field == 'english' else 'state_name_local'
    return _search(connection, name, table='states', alias='s', column=column, order=_ORDER,
                   condition=classification, filter_params=kind_params, mode=mode,
                   max_distance=max_distance, metric=metric, limit=limit)
