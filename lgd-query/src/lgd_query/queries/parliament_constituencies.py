"""Queries for parliament_constituencies; retain supplied rows and report columns.

See docs/datasets/parliament_constituencies.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='parliament_constituencies',
    columns=(
        'parliament_constituency_code',
        'parliament_constituency_name',
        'state_code',
        'state_name',
    ),
    primary_code='parliament_constituency_code', primary_name='parliament_constituency_name',
    order=('state_code', 'parliament_constituency_code'),
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
