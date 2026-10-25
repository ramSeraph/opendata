"""Expose report-specific call signatures without duplicating SQL implementations.

Runtime signatures power help()/inspection; generated .pyi files provide the
same named arguments to editors and type checkers. SQL validation still lives
in the shared implementations.
"""

from functools import wraps
from inspect import Parameter, Signature, signature

from ._dataset import DatasetQueries


def filter_type(spec, column):
    if column in spec.integers:
        return 'int | None'
    if column in ('since', 'until', spec.event_date):
        return 'str | date | None'
    if column in spec.signed or (column.endswith('_code') and column not in (
            'organization_unit_specific_code', 'census_code')):
        return 'str | int | None'
    return 'str | None'


def bind(queries, operation, *, transaction=False):
    method = getattr(queries, operation)
    base = getattr(DatasetQueries, operation)
    parameters = []
    for p in signature(base).parameters.values():
        if p.name == 'self' or p.kind == Parameter.VAR_KEYWORD:
            continue
        annotation = {
            'connection': 'DuckDBPyConnection', 'code': 'str | int',
            'name': 'str', 'field': 'str', 'mode': 'SearchMode',
            'metric': 'DistanceMetric', 'max_distance': 'int',
            'limit': 'int | None', 'year': 'int',
        }[p.name]
        if p.name == 'field':
            annotation = 'Literal[' + ', '.join(repr(name) for name in queries.name_fields) + ']'
        if p.name == 'year':
            annotation = 'Literal[' + ', '.join(str(year) for year in queries.census_years) + ']'
        if transaction and p.name == 'code':
            p = p.replace(name='transaction_id')
            annotation = 'str'
        parameters.append(p.replace(annotation=annotation))
    if 'include_entity_name' in signature(method).parameters:
        parameters.append(Parameter('include_entity_name', Parameter.KEYWORD_ONLY,
                                    default=False, annotation='bool'))
        parameters.append(Parameter('entity_name', Parameter.KEYWORD_ONLY,
                                    default=None, annotation='str | None'))
        parameters.append(Parameter('entity_name_status', Parameter.KEYWORD_ONLY,
                                    default=None, annotation="Literal['matched', 'missing', 'ambiguous'] | None"))
    for column in queries.filters:
        if operation == 'by_code' and column == queries.spec.primary_code:
            continue
        parameters.append(Parameter(column, Parameter.KEYWORD_ONLY, default=None,
                                    annotation=filter_type(queries.spec, column)))
    for name in ('is_null', 'is_blank'):
        parameters.append(Parameter(name, Parameter.KEYWORD_ONLY, default=None,
                                    annotation='Columns'))

    @wraps(method)
    def query(*args, **kwargs):
        if transaction and 'transaction_id' in kwargs:
            kwargs['code'] = kwargs.pop('transaction_id')
        return method(*args, **kwargs)

    query.__signature__ = Signature(parameters, return_annotation='DuckDBPyRelation')
    query.__module__ = f'{__package__}.{queries.spec.dataset}'
    query.__name__ = query.__qualname__ = 'by_id' if transaction else operation
    query.__doc__ = (method.__doc__ or '') + '\n\nAccepted report filters: ' + ', '.join(queries.filters)
    return query


def bind_entities(queries, method, *, entity_type='entity_type', type_annotation='str | int', operation='entities'):
    parameters = [Parameter('connection', Parameter.POSITIONAL_OR_KEYWORD, annotation='DuckDBPyConnection')]
    if operation == 'entities':
        parameters.append(Parameter(entity_type, Parameter.KEYWORD_ONLY, annotation=type_annotation))
    if operation == 'references':
        parameters.append(Parameter('resolution_status', Parameter.KEYWORD_ONLY, default=None,
            annotation="Literal['matched', 'ambiguous', 'missing_type', 'missing_code', 'invalid_code', 'unsupported_type', 'unmatched', 'not_reported'] | None"))
    parameters.extend(Parameter(column, Parameter.KEYWORD_ONLY, default=None,
                                annotation=filter_type(queries.spec, column))
                      for column in queries.filters if column != entity_type or operation != 'entities')
    parameters.extend(Parameter(name, Parameter.KEYWORD_ONLY, default=None, annotation='Columns')
                      for name in ('is_null', 'is_blank'))

    @wraps(method)
    def query(*args, **kwargs):
        return method(*args, **kwargs)

    query.__signature__ = Signature(parameters, return_annotation='DuckDBPyRelation')
    query.__module__ = f'{__package__}.{queries.spec.dataset}'
    query.__name__ = query.__qualname__ = operation
    return query
