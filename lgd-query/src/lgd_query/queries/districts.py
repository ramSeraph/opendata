"""Queries for districts, using the state references in the district report.

Only the ``districts`` view is required. Parent names remain as supplied in
that report, even when the states report spells them differently. Helpers do
not resolve names into parent codes or implicitly load/join the states report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ._missing import Columns, missing_conditions
from ._common import DistanceMetric, SearchMode, census_year, code as _code, search as _search

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection, DuckDBPyRelation


columns = ('district_code', 'district_name', 'state_code', 'state_name', 'district_census_2001_code', 'district_census_2011_code')


def _missing(condition, is_null, is_blank):
    return " AND ".join([condition, *missing_conditions(columns, alias='d',
        nontext=(), is_null=is_null, is_blank=is_blank)])


_ORDER = 'lower(nfc_normalize(trim(d.district_name))), d.state_code, d.district_code'


def _state(state_code):
    if state_code is None:
        return 'TRUE', []
    return 'd.state_code = ?', [_code(state_code)]


def list(connection: DuckDBPyConnection, *, state_code: str | int | None = None,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """List districts, optionally selecting a parent by its LGD state code.

    Results retain all six supplied columns and are ordered by district name,
    state code and district code. No match returns an empty relation.
    """
    condition, params = _state(state_code)
    condition = _missing(condition, is_null, is_blank)
    return connection.sql(f'SELECT d.* FROM districts d WHERE {condition} ORDER BY {_ORDER}', params=params)


def by_code(connection: DuckDBPyConnection, code: str | int, *,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Look up an LGD district code, preserving string codes exactly."""
    return connection.sql('SELECT d.* FROM districts d WHERE d.district_code = ? '
                          f'AND {_missing("TRUE", is_null, is_blank)} ORDER BY {_ORDER}', params=[_code(code)])


def by_census_code(connection: DuckDBPyConnection, code: str | int, *,
                   year: Literal[2001, 2011],
                   state_code: str | int | None = None,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Look up a census code, optionally restricting its LGD parent state.

    Return every matching district; do not assume census codes uniquely identify
    a district across states or years. No zero padding is inferred. state_code
    is an LGD code even though the district lookup uses a census identifier.
    """
    year = census_year(year)
    condition, state_params = _state(state_code)
    condition = _missing(condition, is_null, is_blank)
    return connection.sql(f'SELECT d.* FROM districts d WHERE d.district_census_{year}_code = ? '
                          f'AND {condition} ORDER BY {_ORDER}', params=[_code(code), *state_params])


def search(connection: DuckDBPyConnection, name: str, *,
           state_code: str | int | None = None, mode: SearchMode = 'contains',
           max_distance: int = 2, metric: DistanceMetric = 'levenshtein',
           limit: int | None = 20,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Search district names, optionally within one LGD state.

    The report supplies only an English district-name field. Search uses the
    same trimming, Unicode NFC normalization, case-insensitive literal matching
    and fuzzy distance rules as states.search(). Fuzzy mode adds ``distance``
    and ranks by distance, district name, state code and district code.
    The state filter and distance threshold apply before the result limit.

    DuckDB's edit-distance functions count UTF-8 bytes for non-ASCII text, not
    Unicode characters/graphemes. Returned district and parent names are kept
    verbatim. Helpers never choose one same-named district automatically.
    """
    condition, state_params = _state(state_code)
    condition = _missing(condition, is_null, is_blank)
    return _search(connection, name, table='districts', alias='d', column='district_name',
                   order=_ORDER, condition=condition, filter_params=state_params,
                   mode=mode, max_distance=max_distance, metric=metric, limit=limit)
