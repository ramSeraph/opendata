"""Bound SQL for the report-specific definitions in this package.

Definitions contain trusted column/table identifiers. User values never become
SQL fragments. Name lookups collect alternatives instead of joining rows away
or multiplying relationship/event records.
"""

from dataclasses import dataclass
from datetime import date

from ._common import code as validate_code, search as search_text
from ._missing import missing_conditions


@dataclass(frozen=True)
class NameLookup:
    dataset: str
    name: str
    keys: tuple[tuple[str, str], ...]
    constants: tuple[tuple[str, str], ...] = ()
    # Source columns where the literal code '0' means no supplied reference.
    nonzero_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class Spec:
    dataset: str
    columns: tuple[str, ...]
    primary_code: str
    primary_name: str
    order: tuple[str, ...]
    local_name: str | None = None
    signed: tuple[str, ...] = ()
    integers: tuple[str, ...] = ()
    lookups: tuple[tuple[str, NameLookup | tuple[NameLookup, ...]], ...] = ()
    event_date: str | None = None
    typed_code: bool = False


def _date(value):
    if type(value) is date:
        return value
    if not isinstance(value, str):
        raise ValueError('dates must be YYYY-MM-DD strings or datetime.date values')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('dates must use YYYY-MM-DD')
    return parsed


class DatasetQueries:
    """Implementation shared by modules with separately reviewed report schemas."""

    def __init__(self, spec, *, table=None):
        self.spec = spec
        self._table = table or spec.dataset
        self._lookups = {field: (lookup,) if isinstance(lookup, NameLookup) else lookup
                         for field, lookup in spec.lookups}
        self._names = {c: c for c in spec.columns
                       if c.endswith(('_name', '_name_local')) or c == 'description'}
        self._names['english'] = spec.primary_name
        if spec.local_name:
            self._names['local'] = spec.local_name
        self._names.update({name: name for name in self._lookups})
        self.name_fields = tuple(self._names)
        self.filters = spec.columns + (('since', 'until') if spec.event_date else ())
        stem = spec.primary_code.removesuffix('_code')
        self.census_years = tuple(year for year in (2001, 2011)
                                  if f'{stem}_census_{year}_code' in spec.columns)

    def required_datasets(self, *, field=None):
        """Views needed for listing/lookup, or for search with a selected field."""
        names = [self.spec.dataset]
        if field is not None:
            column = self._field(field)
            if column in self._lookups:
                names.extend(lookup.dataset for lookup in self._lookups[column])
        return tuple(dict.fromkeys(names))

    def _field(self, field):
        if field not in self._names:
            raise ValueError(f'field must be one of: {", ".join(self.name_fields)}')
        return self._names[field]

    def _value(self, column, value):
        if column in self.spec.integers:
            if type(value) is not int or value < 0:
                raise ValueError(f'{column} must be a nonnegative integer')
            return value
        if column == self.spec.event_date:
            return _date(value)
        if column in self.spec.signed:
            text = str(value) if type(value) is int else value
            if not isinstance(text, str) or not text:
                raise ValueError(f'{column} must be signed integer text')
            validate_code(text.removeprefix('-'))
            return text
        # Specific codes, report serials, ward numbers, flags and transaction
        # identifiers are source text. Census/LGD/ECI codes retain their zeros.
        if column.endswith('_code') and column not in ('organization_unit_specific_code', 'census_code'):
            return validate_code(value)
        if not isinstance(value, str):
            raise ValueError(f'{column} must be a string')
        return value

    def _conditions(self, filters):
        filters = dict(filters)
        conditions = missing_conditions(self.spec.columns, alias='t',
            nontext=(*self.spec.integers, self.spec.event_date),
            is_null=filters.pop('is_null', None), is_blank=filters.pop('is_blank', None))
        unknown = set(filters) - set(self.filters)
        if unknown:
            raise ValueError(f'Unsupported {self.spec.dataset} filter(s): {", ".join(sorted(unknown))}')
        params = []
        if (self.spec.typed_code and filters.get('entity_code') is not None
                and not filters.get('entity_type')):
            raise ValueError('entity_type is required with entity_code')
        for column, value in filters.items():
            if value is None:
                continue
            if column in ('since', 'until'):
                conditions.append(f't.{self.spec.event_date} {">=" if column == "since" else "<="} ?')
                params.append(_date(value))
            else:
                conditions.append(f't.{column} = ?')
                params.append(self._value(column, value))
        if filters.get('since') is not None and filters.get('until') is not None:
            if _date(filters['since']) > _date(filters['until']):
                raise ValueError('since must not be later than until')
        return ' AND '.join(conditions) or 'TRUE', params

    @property
    def _order(self):
        columns = [f'lower(nfc_normalize(trim(t.{self.spec.primary_name})))']
        if self.spec.event_date:
            columns.insert(0, f't.{self.spec.event_date}')
        columns.extend(f't.{c}' for c in self.spec.order)
        return ', '.join(columns)

    def list(self, connection, **filters):
        """Return supplied rows, narrowed by exact, named report-column filters.

        Events also accept inclusive ``since``/``until`` dates. No rows are
        deduplicated. None means the corresponding filter is not applied.
        """
        condition, params = self._conditions(filters)
        return connection.sql(f'SELECT t.* FROM {self._table} t '
                              f'WHERE {condition} ORDER BY {self._order}', params=params)

    def by_code(self, connection, code, **filters):
        """Find all rows for the documented primary code, with optional scope.

        This is not a uniqueness assertion. Census codes use by_census_code;
        polymorphic entity codes require an entity_type filter.
        """
        if self.spec.primary_code in filters:
            raise ValueError(f'{self.spec.primary_code} was already supplied positionally')
        value = self._value(self.spec.primary_code, code)
        return self.list(connection, **{self.spec.primary_code: value}, **filters)

    def by_census_code(self, connection, code, *, year, **filters):
        """Look up the primary entity's code in an explicit census year."""
        if type(year) is not int or year not in self.census_years:
            raise ValueError(f'year must be one of: {self.census_years}')
        column = f'{self.spec.primary_code.removesuffix("_code")}_census_{year}_code'
        if column in filters:
            raise ValueError(f'{column} was already supplied positionally')
        return self.list(connection, **{column: self._value(column, code)}, **filters)

    def search(self, connection, name, *, field='english', mode='contains',
               max_distance=2, metric='levenshtein', limit=20, **filters):
        """Search a reported name or an explicitly configured code-based lookup.

        Accepts exact/prefix/contains/fuzzy matching. Filters and distance
        thresholds precede limits. Lookup searches add ``lookup_names`` with
        all resolved alternatives, preserving the source row count. Missing
        references do not match. Fuzzy searches add the best ``distance``.
        """
        column = self._field(field)
        condition, params = self._conditions(filters)
        if column not in self._lookups:
            return search_text(connection, name, table=self._table, alias='t',
                               column=column, order=self._order, condition=condition,
                               filter_params=params, mode=mode, max_distance=max_distance,
                               metric=metric, limit=limit)
        table = f'(SELECT s.*, {self._lookup_names(column)} AS lookup_names FROM {self._table} s)'
        return search_text(connection, name, table=table, alias='t', column='lookup_names',
                           order=self._order, condition=condition, filter_params=params,
                           mode=mode, max_distance=max_distance, metric=metric, limit=limit,
                           multiple_names=True)

    def _lookup_names(self, column, *, alias='s'):
        """SQL array of labels for a package-defined lookup and row alias."""
        alternatives = []
        for lookup in self._lookups[column]:
            joins = ' AND '.join(f'n.{target} = {alias}.{source} AND '
                                 f"NULLIF(trim({alias}.{source}), '') IS NOT NULL"
                                 for source, target in lookup.keys)
            for key, value in lookup.constants:
                # Values are package-owned scope constants, never caller input.
                joins += f" AND n.{key} = '" + value.replace("'", "''") + "'"
            for key in lookup.nonzero_keys:
                joins += f" AND {alias}.{key} <> '0'"
            alternatives.append(f'SELECT n.{lookup.name} AS label FROM {lookup.dataset} n '
                                f"WHERE {joins} AND NULLIF(trim(n.{lookup.name}), '') IS NOT NULL")
        return ('ARRAY(SELECT DISTINCT label FROM (' + ' UNION ALL '.join(alternatives) +
                ') names ORDER BY label)')
