"""Queries for gp_mapping; retain supplied rows and report columns.

See docs/datasets/gp_mapping.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='gp_mapping',
    columns=(
        'village_code',
        'village_name',
        'local_body_code',
        'local_body_name',
        'subdistrict_code',
        'subdistrict_name',
        'district_code',
        'district_name',
        'state_code',
        'state_name',
        'village_census_2011_code',
        'village_census_2001_code',
        'subdistrict_census_2011_code',
        'subdistrict_census_2001_code',
        'district_census_2011_code',
        'district_census_2001_code',
    ),
    primary_code='village_code', primary_name='village_name',
    order=('state_code', 'district_code', 'subdistrict_code', 'village_code', 'local_body_code', 'village_census_2011_code', 'village_census_2001_code', 'subdistrict_census_2011_code', 'subdistrict_census_2001_code', 'district_census_2011_code', 'district_census_2001_code'),
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
