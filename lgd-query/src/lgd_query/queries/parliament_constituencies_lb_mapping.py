"""Queries for parliament_constituencies_lb_mapping; retain supplied rows and report columns.

See docs/datasets/parliament_constituencies_lb_mapping.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, NameLookup, Spec


_queries = DatasetQueries(Spec(
    dataset='parliament_constituencies_lb_mapping',
    columns=(
        'parliament_constituency_code',
        'parliament_constituency_name',
        'assembly_constituency_name',
        'local_body_name',
        'local_body_type_name',
        'coverage_type',
        'state_code',
    ),
    primary_code='parliament_constituency_code', primary_name='parliament_constituency_name',
    order=('state_code', 'parliament_constituency_code'),
    local_name=None,
    signed=(), integers=(),
    lookups=(
        ('state_name', NameLookup('states', 'state_name', (('state_code', 'state_code'),))),
    ),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
