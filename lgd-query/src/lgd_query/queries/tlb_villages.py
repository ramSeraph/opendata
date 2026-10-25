"""Queries for tlb_villages; retain supplied rows and report columns.

See docs/datasets/tlb_villages.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='tlb_villages',
    columns=(
        'village_code',
        'village_name',
        'local_body_code',
        'local_body_name',
        'local_body_type_code',
        'local_body_type_name',
        'block_code',
        'block_name',
        'subdistrict_code',
        'subdistrict_name',
        'district_code',
        'district_name',
        'state_code',
        'state_name',
        'state_census_2011_code',
        'district_census_2011_code',
        'subdistrict_census_2011_code',
        'village_census_2011_code',
    ),
    primary_code='village_code', primary_name='village_name',
    order=('state_code', 'district_code', 'subdistrict_code', 'village_code', 'local_body_code', 'local_body_type_code', 'block_code', 'state_census_2011_code', 'district_census_2011_code', 'subdistrict_census_2011_code', 'village_census_2011_code'),
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
