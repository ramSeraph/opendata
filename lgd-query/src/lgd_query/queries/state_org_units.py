"""Queries for state_org_units; retain supplied rows and report columns.

See docs/datasets/state_org_units.md for identifiers, filters and dependencies.
"""

from ._dataset import NameLookup, Spec
from ._org_units import OrganizationUnitQueries
from ._org_entities import OrganizationEntityQueries


_queries = OrganizationUnitQueries(Spec(
    dataset='state_org_units',
    columns=(
        'organization_unit_code',
        'organization_unit_name',
        'organization_unit_name_local',
        'entity_type',
        'entity_code',
        'parent_organization_unit_code',
        'parent_organization_unit_name',
        'organization_level_code',
        'organization_code',
        'organization_name',
        'state_code',
        'state_name',
    ),
    primary_code='organization_unit_code', primary_name='organization_unit_name',
    order=('state_code', 'organization_unit_code', 'entity_code', 'parent_organization_unit_code', 'organization_level_code', 'organization_code'),
    local_name='organization_unit_name_local',
    signed=('entity_type', 'entity_code'), integers=(),
    lookups=(
        ('entity_name', NameLookup('org_unit_details', 'entity_name', (
            ('organization_unit_code', 'organization_unit_code'),
            ('organization_code', 'organization_code'), ('state_code', 'state_code'),
            ('entity_code', 'entity_code'), ('entity_type', 'entity_type')))),
        # Match the unit's own level code to a named report selection. A
        # coverage row's selection is not necessarily that row's unit level.
        ('organization_level_name', NameLookup('org_unit_coverage', 'report_organization_level_name', (
            ('organization_level_code', 'report_organization_level_code'),
            ('organization_code', 'organization_code'), ('state_code', 'state_code')))),
    ),
))

list = _queries.list
search = _queries.search
by_code = _queries.by_code
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years

_entities = OrganizationEntityQueries(_queries)
entities = _entities.entities
entity_sources = _entities.entity_sources
required_entity_datasets = _entities.required_entity_datasets
entity_type_filter = _entities.entity_type_filter
