"""Queries for blocks; retain supplied rows and report columns.

See docs/datasets/blocks.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='blocks',
    columns=(
        'block_code',
        'block_version',
        'block_name',
        'block_name_local',
        'district_code',
        'district_name',
        'state_code',
        'state_name',
    ),
    primary_code='block_code', primary_name='block_name',
    order=('state_code', 'district_code', 'block_code'),
    local_name='block_name_local',
    signed=(), integers=('block_version',),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
