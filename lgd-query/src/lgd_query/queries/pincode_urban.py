"""Queries for pincode_urban; retain supplied rows and report columns.

See docs/datasets/pincode_urban.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='pincode_urban',
    columns=(
        'local_body_code',
        'local_body_name',
        'local_body_type_name',
        'pincode',
        'state_code',
        'state_name',
    ),
    primary_code='local_body_code', primary_name='local_body_name',
    order=('state_code', 'local_body_code'),
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
