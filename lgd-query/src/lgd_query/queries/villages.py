"""Queries for villages; retain supplied rows and report columns.

See docs/datasets/villages.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='villages',
    columns=(
        'village_code',
        'village_version',
        'village_name',
        'village_name_local',
        'village_status',
        'village_category',
        'remark',
        'state_code',
        'state_name',
        'district_code',
        'district_name',
        'subdistrict_code',
        'subdistrict_name',
        'village_census_2001_code',
        'village_census_2011_code',
    ),
    primary_code='village_code', primary_name='village_name',
    order=('state_code', 'district_code', 'subdistrict_code', 'village_code', 'village_category', 'village_census_2001_code', 'village_census_2011_code'),
    local_name='village_name_local',
    signed=(), integers=('village_version',),
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
by_census_code = bind(_queries, 'by_census_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
