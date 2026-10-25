"""Queries for district_panchayats; retain supplied rows and report columns.

See docs/datasets/district_panchayats.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='district_panchayats',
    columns=(
        'district_panchayat_code',
        'district_panchayat_name',
        'district_code',
        'district_name',
        'state_code',
        'state_name',
    ),
    primary_code='district_panchayat_code', primary_name='district_panchayat_name',
    order=('state_code', 'district_code', 'district_panchayat_code'),
    local_name=None,
    signed=(), integers=(),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
