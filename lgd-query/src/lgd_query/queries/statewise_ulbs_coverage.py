"""Queries for statewise_ulbs_coverage; retain supplied rows and report columns.

See docs/datasets/statewise_ulbs_coverage.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='statewise_ulbs_coverage',
    columns=(
        'local_body_code',
        'local_body_name',
        'district_code',
        'district_name',
        'subdistrict_code',
        'subdistrict_name',
        'village_code',
        'village_name',
        'state_name',
        'local_body_census_2011_code',
    ),
    primary_code='local_body_code', primary_name='local_body_name',
    order=('district_code', 'subdistrict_code', 'local_body_code', 'village_code', 'local_body_census_2011_code'),
    local_name=None,
    signed=(), integers=(),
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
by_census_code = bind(_queries, 'by_census_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
