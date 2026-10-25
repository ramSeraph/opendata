"""Queries for state_orgs; retain supplied rows and report columns.

See docs/datasets/state_orgs.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='state_orgs',
    columns=(
        'organization_code',
        'organization_name',
        'organization_type',
        'parent_organization_code',
        'parent_organization_name',
        'parent_organization_type',
        'state_code',
        'state_name',
    ),
    primary_code='organization_code', primary_name='organization_name',
    order=('state_code', 'organization_code', 'parent_organization_code'),
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
