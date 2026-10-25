"""Queries for transactions; retain supplied rows and report columns.

See docs/datasets/transactions.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='transactions',
    columns=(
        'transaction_id',
        'operation_code',
        'operation_name',
        'description',
        'transaction_date',
        'state_code',
        'state_name',
    ),
    primary_code='transaction_id', primary_name='description',
    order=('state_code', 'transaction_id', 'operation_code'),
    local_name=None,
    signed=(), integers=(),
    event_date='transaction_date',
))

list = _queries.list
search = _queries.search
by_id = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
