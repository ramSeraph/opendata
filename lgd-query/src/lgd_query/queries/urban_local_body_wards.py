"""Queries for urban_local_body_wards; retain supplied rows and report columns.

See docs/datasets/urban_local_body_wards.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='urban_local_body_wards',
    columns=(
        'ward_code',
        'ward_number',
        'ward_name',
        'local_body_code',
        'local_body_name',
        'state_code',
        'state_name',
        'local_body_census_2011_code',
    ),
    primary_code='ward_code', primary_name='ward_name',
    order=('state_code', 'ward_code', 'ward_number', 'local_body_code', 'local_body_census_2011_code'),
    local_name=None,
    signed=(), integers=(),
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
