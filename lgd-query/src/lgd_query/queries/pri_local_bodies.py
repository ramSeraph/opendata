"""Queries for pri_local_bodies; retain supplied rows and report columns.

See docs/datasets/pri_local_bodies.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, NameLookup, Spec


_queries = DatasetQueries(Spec(
    dataset='pri_local_bodies',
    columns=(
        'local_body_code',
        'local_body_version',
        'local_body_name',
        'local_body_name_local',
        'local_body_type_code',
        'local_body_type_name',
        'parent_local_body_code',
        'state_code',
        'state_name',
    ),
    primary_code='local_body_code', primary_name='local_body_name',
    order=('state_code', 'local_body_code', 'local_body_type_code', 'parent_local_body_code'),
    local_name='local_body_name_local',
    signed=(), integers=('local_body_version',),
    lookups=(
        ('parent_local_body_name', NameLookup('pri_local_bodies', 'local_body_name', (('parent_local_body_code', 'local_body_code'), ('state_code', 'state_code')))),
    ),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
