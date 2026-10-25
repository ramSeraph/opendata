"""Queries for assembly_constituencies; retain supplied rows and report columns.

See docs/datasets/assembly_constituencies.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='assembly_constituencies',
    columns=(
        'assembly_constituency_code',
        'assembly_constituency_name',
        'parliament_constituency_code',
        'parliament_constituency_name',
        'state_code',
        'state_name',
    ),
    primary_code='assembly_constituency_code', primary_name='assembly_constituency_name',
    order=('state_code', 'assembly_constituency_code', 'parliament_constituency_code'),
    local_name=None,
    signed=(), integers=(),
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
