"""Queries for urban_local_bodies; retain supplied rows and report columns.

See docs/datasets/urban_local_bodies.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='urban_local_bodies',
    columns=(
        'local_body_code',
        'local_body_version',
        'local_body_name',
        'local_body_name_local',
        'local_body_type_code',
        'local_body_census_2011_code',
        'state_code',
        'state_name',
    ),
    primary_code='local_body_code', primary_name='local_body_name',
    order=('state_code', 'local_body_code', 'local_body_type_code', 'local_body_census_2011_code'),
    local_name='local_body_name_local',
    signed=(), integers=('local_body_version',),
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
by_census_code = bind(_queries, 'by_census_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
