"""Queries for changes; retain supplied rows and report columns.

See docs/datasets/changes.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='changes',
    columns=(
        'report_serial',
        'entity_type',
        'entity_code',
        'entity_version',
        'entity_name',
        'entity_name_local',
        'census_code',
        'operation_name',
        'report_date',
    ),
    primary_code='entity_code', primary_name='entity_name',
    order=('entity_code', 'census_code'),
    local_name='entity_name_local',
    signed=(), integers=('entity_version',),
    event_date='report_date',
    typed_code=True,
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
