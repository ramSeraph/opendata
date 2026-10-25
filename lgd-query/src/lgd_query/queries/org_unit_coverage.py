"""Queries for org_unit_coverage; retain supplied rows and report columns.

See docs/datasets/org_unit_coverage.md for identifiers, filters and dependencies.
"""

from ._dataset import DatasetQueries, Spec
from ._org_entities import OrganizationEntityQueries


_queries = DatasetQueries(Spec(
    dataset='org_unit_coverage',
    columns=(
        'organization_unit_code',
        'organization_unit_name',
        'entity_code',
        'entity_name',
        'organization_unit_specific_code',
        'covered_entity_code',
        'covered_entity_name',
        'covered_entity_type',
        'coverage_type',
        'coverage_details_reported',
        'report_organization_level_code',
        'report_organization_level_name',
        'organization_code',
        'organization_name',
        'state_code',
        'state_name',
    ),
    primary_code='organization_unit_code', primary_name='organization_unit_name',
    order=('state_code', 'organization_unit_code', 'entity_code', 'organization_unit_specific_code', 'covered_entity_code', 'report_organization_level_code', 'organization_code'),
    local_name=None,
    signed=('entity_code',), integers=(),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years

_entities = OrganizationEntityQueries(_queries, coverage=True)
entities = _entities.entities
entity_sources = _entities.entity_sources
required_entity_datasets = _entities.required_entity_datasets
entity_type_filter = _entities.entity_type_filter
