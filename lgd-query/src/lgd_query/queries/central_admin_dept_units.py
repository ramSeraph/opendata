"""Queries for central_admin_dept_units; retain supplied rows and report columns.

See docs/datasets/central_admin_dept_units.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='central_admin_dept_units',
    columns=(
        'administrative_unit_code',
        'administrative_unit_name',
        'administrative_unit_name_local',
        'administrative_unit_level_code',
        'administrative_unit_level_name',
    ),
    primary_code='administrative_unit_code', primary_name='administrative_unit_name',
    order=('administrative_unit_code', 'administrative_unit_level_code'),
    local_name='administrative_unit_name_local',
    signed=(), integers=(),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
