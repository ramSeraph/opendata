"""Queries for state_org_designations; retain supplied rows and report columns.

See docs/datasets/state_org_designations.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='state_org_designations',
    columns=(
        'designation_code',
        'designation_name',
        'designation_name_local',
        'organization_level_code',
        'organization_level_name',
        'organization_code',
        'organization_name',
        'state_code',
        'state_name',
    ),
    primary_code='designation_code', primary_name='designation_name',
    order=('state_code', 'designation_code', 'organization_level_code', 'organization_code'),
    local_name='designation_name_local',
    signed=(), integers=(),
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
