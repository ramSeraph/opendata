"""Queries using the parent references supplied in the subdistrict report.

Only the ``subdistricts`` view is required. District/state names and the
subdistrict version remain as reported; no parent dataset is loaded or joined.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ._missing import Columns, missing_conditions
from ._common import DistanceMetric, SearchMode, census_year, code as _code, search as _search

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection, DuckDBPyRelation


columns = ('subdistrict_code', 'subdistrict_version', 'subdistrict_name', 'district_code', 'district_name', 'state_code', 'state_name', 'subdistrict_census_2001_code', 'subdistrict_census_2011_code')


def _missing(condition, is_null, is_blank):
    return " AND ".join([condition, *missing_conditions(columns, alias='t',
        nontext=('subdistrict_version',), is_null=is_null, is_blank=is_blank)])


_ORDER = ('lower(nfc_normalize(trim(t.subdistrict_name))), '
          't.state_code, t.district_code, t.subdistrict_code')


def _parents(state_code, district_code):
    conditions, params = [], []
    for column, value in (('state_code', state_code), ('district_code', district_code)):
        if value is not None:
            conditions.append(f't.{column} = ?')
            params.append(_code(value))
    return ' AND '.join(conditions) or 'TRUE', params


def list(connection: DuckDBPyConnection, *, state_code: str | int | None = None,
         district_code: str | int | None = None,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """List subdistricts, optionally within an LGD state and/or district.

    Both supplied filters must match the row. No hierarchy is inferred from
    other datasets. Results retain all nine source columns, ordered by name,
    state code, district code and subdistrict code. No match is an empty relation.
    """
    condition, params = _parents(state_code, district_code)
    condition = _missing(condition, is_null, is_blank)
    return connection.sql(f'SELECT t.* FROM subdistricts t WHERE {condition} '
                          f'ORDER BY {_ORDER}', params=params)


def by_code(connection: DuckDBPyConnection, code: str | int, *,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Look up an LGD subdistrict code, preserving string codes exactly."""
    return connection.sql('SELECT t.* FROM subdistricts t WHERE t.subdistrict_code = ? '
                          f'AND {_missing("TRUE", is_null, is_blank)} ORDER BY {_ORDER}', params=[_code(code)])


def by_census_code(connection: DuckDBPyConnection, code: str | int, *,
                   year: Literal[2001, 2011], state_code: str | int | None = None,
                   district_code: str | int | None = None,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Look up a census identifier, optionally restricting both LGD parents.

    All matches are retained; do not assume uniqueness across districts, states
    or years. Parent filters are LGD codes even though the lookup uses a census
    identifier. String codes retain leading zeros; no padding is inferred.
    """
    year = census_year(year)
    condition, parent_params = _parents(state_code, district_code)
    condition = _missing(condition, is_null, is_blank)
    return connection.sql(f'SELECT t.* FROM subdistricts t WHERE '
                          f't.subdistrict_census_{year}_code = ? AND {condition} '
                          f'ORDER BY {_ORDER}', params=[_code(code), *parent_params])


def search(connection: DuckDBPyConnection, name: str, *,
           state_code: str | int | None = None, district_code: str | int | None = None,
           mode: SearchMode = 'contains', max_distance: int = 2,
           metric: DistanceMetric = 'levenshtein', limit: int | None = 20,
           is_null: Columns = None, is_blank: Columns = None) -> DuckDBPyRelation:
    """Search reported subdistrict names, optionally within both LGD parents.

    Uses states.search()'s normalization, literal matching and fuzzy rules.
    There is no local-name field in this report. All supplied parent filters
    and the distance threshold apply before the limit. Fuzzy results add
    ``distance`` and rank by distance before name/state/district/subdistrict code.

    DuckDB's edit-distance functions count UTF-8 bytes for non-ASCII text, not
    Unicode characters/graphemes. Names are not transliterated or replaced with
    names from parent reports. Same-named subdistricts remain separate results.
    """
    condition, parent_params = _parents(state_code, district_code)
    condition = _missing(condition, is_null, is_blank)
    return _search(connection, name, table='subdistricts', alias='t', column='subdistrict_name',
                   order=_ORDER, condition=condition, filter_params=parent_params,
                   mode=mode, max_distance=max_distance, metric=metric, limit=limit)
