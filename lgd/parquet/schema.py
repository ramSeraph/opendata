"""Canonical source-field vocabulary and stable field identity validation."""

import hashlib
import json


# This is the reviewed vocabulary, independent of individual dataset schemas.
# New concepts must be registered here; source-header aliases belong in readers.
# Codes and source flags remain strings, even when all sampled values are numeric.
FIELD_TYPES = {
    **dict.fromkeys('''
        administrative_unit_code administrative_unit_level_code administrative_unit_level_name
        administrative_unit_level_name_local administrative_unit_name administrative_unit_name_local
        assembly_constituency_code assembly_constituency_eci_code assembly_constituency_name
        block_code block_district_code block_district_name block_name block_name_local
        census_code constituency_level constituency_code coverage_type coverage_details_reported covered_entity_code covered_entity_name
        covered_entity_type created_by created_on description designation_code designation_name
        designation_name_local district_census_2001_code district_census_2011_code district_code
        district_name district_panchayat_code district_panchayat_name entity_code entity_name
        entity_name_local entity_type entity_type_name hierarchy intermediate_panchayat_code intermediate_panchayat_name
        is_active local_body_census_2011_code local_body_code local_body_level local_body_name
        local_body_name_local local_body_type_code local_body_type_name operation_code operation_name
        organization_code organization_level_code organization_level_name organization_located_at_levels
        organization_name organization_type organization_unit_code organization_unit_name
        organization_unit_name_local organization_unit_specific_code organization_unit_email
        organization_unit_contact_number organization_unit_address overlap_unit parent_administrative_code parent_category
        parent_local_body_code parent_organization_code parent_organization_level_code
        parent_organization_name parent_organization_type parent_organization_unit_code
        parent_organization_unit_name parliament_constituency_code parliament_constituency_eci_code
        parliament_constituency_name pincode publication_status remark report_serial revenue_entity
        report_organization_level_code report_organization_level_name
        state_census_2001_code state_census_2011_code state_code state_name
        state_name_local state_or_ut subdistrict_census_2001_code subdistrict_census_2011_code
        subdistrict_code subdistrict_name transaction_id unit_level_type village_category
        village_census_2001_code village_census_2011_code village_code village_name village_name_local
        village_status ward_code ward_name ward_name_local ward_number
    '''.split(), 'VARCHAR'),
    **dict.fromkeys('''block_version entity_version local_body_version state_version
                       subdistrict_version village_version'''.split(), 'INTEGER'),
    **dict.fromkeys('report_date transaction_date'.split(), 'DATE'),
}


def validate_fields(dataset, fields, *, extra_types=None):
    """Reject unreviewed synonyms, incompatible types and reused field identities."""
    types = FIELD_TYPES | (extra_types or {})
    ids, names = set(), set()
    for field_id, name, kind, *_ in fields:
        if field_id in ids or name in names or field_id <= 0:
            raise ValueError(f'{dataset}: duplicate/invalid field identity: {field_id} {name}')
        if name not in types:
            raise ValueError(f'{dataset}: unregistered canonical field: {name}')
        if kind != types[name]:
            raise ValueError(f'{dataset}: {name} must be {types[name]}, not {kind}')
        ids.add(field_id)
        names.add(name)


def schema_id(fields):
    return hashlib.sha256(json.dumps(sorted(fields), separators=(',', ':')).encode()).hexdigest()
