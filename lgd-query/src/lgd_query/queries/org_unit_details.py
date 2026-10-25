"""Queries for org_unit_details; retain supplied rows and report columns.

See docs/datasets/org_unit_details.md for identifiers, filters and dependencies.
"""

from ._signatures import bind, bind_entities
from ._dataset import DatasetQueries, Spec
from ._org_entities import OrganizationEntityQueries


_queries = DatasetQueries(Spec(
    dataset='org_unit_details',
    columns=(
        'organization_unit_code',
        'organization_unit_name',
        'parent_organization_unit_code',
        'parent_organization_unit_name',
        'organization_unit_specific_code',
        'organization_unit_email',
        'organization_unit_contact_number',
        'organization_unit_address',
        'entity_type',
        'entity_type_name',
        'entity_code',
        'entity_name',
        'organization_code',
        'organization_name',
        'state_code',
        'state_name',
    ),
    primary_code='organization_unit_code', primary_name='organization_unit_name',
    order=('state_code', 'organization_unit_code', 'parent_organization_unit_code', 'organization_unit_specific_code', 'entity_code', 'organization_code'),
    local_name=None,
    signed=('entity_type', 'entity_code'), integers=(),
))

list = bind(_queries, 'list')
search = bind(_queries, 'search')
by_code = bind(_queries, 'by_code')
required_datasets = _queries.required_datasets
name_fields = _queries.name_fields
filters = _queries.filters
census_years = _queries.census_years

_entities = OrganizationEntityQueries(_queries)
entities = bind_entities(_queries, _entities.entities)
entity_sources = _entities.entity_sources
required_entity_datasets = _entities.required_entity_datasets
entity_type_filter = _entities.entity_type_filter

references = bind_entities(_queries, _entities.references, entity_type='entity_type', operation='references')
reference_types = bind_entities(_queries, _entities.reference_types, entity_type='entity_type', operation='reference_types')
required_reference_datasets = _entities.required_reference_datasets
reference_sources = _entities.reference_sources
reference_type_map = _entities.reference_type_map
