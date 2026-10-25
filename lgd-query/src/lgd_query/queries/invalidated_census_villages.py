"""Queries for invalidated_census_villages; retain supplied rows and report columns.

See docs/datasets/invalidated_census_villages.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='invalidated_census_villages',
    columns=(
        'village_code',
        'village_name',
        'state_code',
        'state_name',
        'village_census_2001_code',
        'village_census_2011_code',
    ),
    primary_code='village_code', primary_name='village_name',
    order=('state_code', 'village_code', 'village_census_2001_code', 'village_census_2011_code'),
    local_name=None,
    signed=(), integers=(),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
by_census_code = _queries.by_census_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
