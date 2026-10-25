"""Queries for pri_local_body_wards; retain supplied rows and report columns.

See docs/datasets/pri_local_body_wards.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='pri_local_body_wards',
    columns=(
        'ward_code',
        'ward_number',
        'ward_name',
        'local_body_code',
        'local_body_name',
        'state_code',
        'state_name',
        'ward_name_local',
        'local_body_type_name',
        'district_panchayat_name',
        'intermediate_panchayat_name',
    ),
    primary_code='ward_code', primary_name='ward_name',
    order=('state_code', 'ward_code', 'ward_number', 'local_body_code'),
    local_name='ward_name_local',
    signed=(), integers=(),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
