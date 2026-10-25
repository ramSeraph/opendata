"""Queries for central_admin_depts; retain supplied rows and report columns.

See docs/datasets/central_admin_depts.md for identifiers, filters and dependencies.
"""

from ._signatures import bind
from ._dataset import DatasetQueries, Spec


_queries = DatasetQueries(Spec(
    dataset='central_admin_depts',
    columns=(
        'administrative_unit_level_code',
        'administrative_unit_level_name',
        'parent_administrative_code',
        'organization_level_code',
        'administrative_unit_level_name_local',
        'created_by',
        'created_on',
        'hierarchy',
        'is_active',
        'publication_status',
        'local_body_level',
        'organization_located_at_levels',
        'overlap_unit',
        'parent_category',
        'parent_organization_level_code',
        'revenue_entity',
        'unit_level_type',
    ),
    primary_code='administrative_unit_level_code', primary_name='administrative_unit_level_name',
    order=('administrative_unit_level_code', 'parent_administrative_code', 'organization_level_code', 'parent_organization_level_code'),
    local_name='administrative_unit_level_name_local',
    signed=('parent_administrative_code',), integers=(),
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years
