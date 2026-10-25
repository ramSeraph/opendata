"""Compile existing query helpers without opening a database or fetching data."""

from __future__ import annotations

from dataclasses import dataclass, field
from inspect import signature
from typing import TYPE_CHECKING, Any

from ._catalog import get, required_datasets
from ._dataset import _date
from ._org_entities import TYPE_COLUMNS
from ._org_units import wants_entity_name

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection, DuckDBPyRelation
    from ..metadata import Dataset, Release


def columns_for(dataset):
    module = get(dataset)
    return module._queries.spec.columns if hasattr(module, '_queries') else module.columns


@dataclass(frozen=True)
class _Statement:
    sql: str
    params: tuple
    columns: tuple[str, ...]

    def query(self, alias, sql):
        # Alias and SQL are supplied by our helper implementations. Wrapping
        # the earlier statement preserves its bound values and ordering.
        return _Statement(f'WITH "{alias}" AS ({self.sql}) {sql}', self.params, self.columns)


class _SQLBuilder:
    """The small SQL-building interface used by the connection-taking helpers."""

    def __init__(self, columns):
        self.columns = columns

    def sql(self, sql, *, params):
        return _Statement(sql, tuple(params), self.columns)


@dataclass(frozen=True)
class PreparedQuery:
    """Validated SQL and dependencies; execute against caller-owned views.

    Preparation checks Python arguments without importing DuckDB. SQL binding
    and the actual input schemas are checked by DuckDB during execute().
    """

    dataset: str
    operation: str
    required_datasets: tuple[str, ...]
    columns: tuple[str, ...]
    _statement: _Statement = field(repr=False)

    def sources(self, release: Release, *, observed_on: str | None = None) -> tuple[Dataset, ...]:
        """Resolve all dependencies from one pinned release, without network I/O."""
        if observed_on is not None:
            observed_on = _date(observed_on).isoformat()
        return tuple(release.dataset(name, observed_on=observed_on) for name in self.required_datasets)

    def execute(self, connection: DuckDBPyConnection) -> DuckDBPyRelation:
        """Return a native relation; no views, downloads or connections are created."""
        return connection.sql(self._statement.sql, params=list(self._statement.params))


def prepare(dataset: str, operation: str, *args: Any, **options: Any) -> PreparedQuery:
    """Prepare list, code/census/id lookup, search, entities, references or types.

    Arguments after operation are those of the dataset helper, excluding its
    connection. Use .sources(release) with lgd_query.connect(), then .execute(db).
    """
    module = get(dataset)
    if operation not in ('list', 'by_code', 'by_id', 'by_census_code', 'search', 'entities', 'eci_codes',
                         'references', 'reference_types'):
        raise ValueError(f'Unsupported query operation: {operation!r}')
    method = getattr(module, operation, None)
    if method is None:
        raise ValueError(f'{dataset} does not support {operation}')
    # Binding also catches missing/unsupported keyword arguments before I/O.
    bound = signature(method).bind(None, *args, **options)
    values = dict(bound.arguments)
    values.pop('connection', None)
    values.update(values.pop('filters', {}))
    values.update(values.pop('options', {}))
    columns = columns_for(dataset)
    if operation == 'entities':
        field = getattr(module, 'entity_type_filter', 'entity_type')
        if field not in values:
            raise ValueError(f'{field} is required')
        scope = {'state_code': values.get('state_code')} if hasattr(module, '_entities') else {}
        dependencies = module.required_entity_datasets(values[field], **scope)
        columns = ('entity_dataset', 'entity_type', 'entity_code', 'entity_name')
        if dataset != 'constituency_coverage':
            columns += ('reference_type_matches',)
        columns = tuple(dict.fromkeys((*columns, *(column for dependency in dependencies[1:]
                                                   for column in columns_for(dependency)))))
    elif operation == 'references':
        reference_type = values.get(module.entity_type_filter)
        dependencies = module.required_reference_datasets(reference_type, state_code=values.get('state_code'))
        columns = module._entities.reference_columns(reference_type, state_code=values.get('state_code'))
    elif operation == 'reference_types':
        dependencies = (dataset,)
        columns = TYPE_COLUMNS
    else:
        field = values.get('field', 'english') if operation == 'search' else None
        name_options = {key: values[key] for key in
            ('include_entity_name', 'entity_name', 'entity_name_status', 'is_null', 'is_blank') if key in values}
        dependencies = required_datasets(dataset, field=field, **name_options)
        enriched = dataset in ('state_org_units', 'central_org_units') and wants_entity_name(**name_options)
        if enriched:
            columns += ('entity_names', 'entity_name', 'entity_name_status')
        if operation == 'search':
            if hasattr(module, '_queries') and module._queries._field(field) in module._queries._lookups:
                columns += ('lookup_names',)
            if values.get('mode') == 'fuzzy':
                columns += ('distance',)
        if operation == 'eci_codes':
            level = values.get('level')
            if level not in module.eci_levels:
                raise ValueError('level must be parliament or assembly')
            columns = ('source_dataset', 'state_code', f'{level}_constituency_code',
                       f'{level}_constituency_eci_code', 'lookup_names',
                       'conflicting_eci_codes', 'eci_code_reused')
    statement = method(_SQLBuilder(columns), *args, **options)
    return PreparedQuery(dataset, operation, dependencies, columns, statement)
