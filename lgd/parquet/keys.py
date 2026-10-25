"""Reported record identities; these are not guaranteed foreign keys."""


from .organizations import KEYS as ORGANIZATION_KEYS


ROW_KEYS = {
    **ORGANIZATION_KEYS,
    'org_unit_coverage': ['organization_unit_code', 'covered_entity_type', 'covered_entity_code'],
    'nofn_panchayats': ['local_body_code', 'state_code', 'district_name', 'subdistrict_name'],
    'state_orgs': ['organization_code'],
    'central_orgs': ['organization_code'],
    'pincode_villages': ['village_code', 'pincode'],
    'pincode_urban': ['local_body_code', 'pincode'],
    'invalidated_census_villages': ['village_code'],
    'constituencies_mapping_urban': ['ward_code', 'assembly_constituency_code', 'subdistrict_code', 'district_code'],
    'constituencies_mapping_pri': ['village_code', 'local_body_code', 'block_code', 'constituency_level', 'constituency_code'],
    'parliament_constituencies_lb_mapping': ['parliament_constituency_code', 'assembly_constituency_name', 'local_body_name', 'local_body_type_name'],
    'constituency_coverage': ['entity_code', 'entity_type', 'constituency_level', 'constituency_code'],
    'parliament_constituencies': ['parliament_constituency_code'],
    'assembly_constituencies': ['assembly_constituency_code'],
    'tlb_villages': ['village_code', 'block_code', 'local_body_code', 'state_code', 'district_code', 'subdistrict_code'],
    'statewise_ulbs_coverage': ['local_body_code', 'district_code', 'subdistrict_code', 'village_code'],
    'district_panchayats': ['district_panchayat_code', 'district_code'],
    'pri_local_body_wards': ['ward_code'],
    'urban_local_body_wards': ['ward_code'],
    'villages_by_blocks': ['village_code', 'block_code', 'local_body_code', 'state_code', 'district_code', 'subdistrict_code'],
    'gp_mapping': ['village_code', 'local_body_code'],
    'states': ['state_code'],
    'districts': ['district_code'],
    'subdistricts': ['subdistrict_code'],
    'blocks': ['block_code', 'district_code'],
    'urban_local_bodies': ['local_body_code'],
    'pri_local_bodies': ['local_body_code'],
    'traditional_local_bodies': ['local_body_code', 'district_panchayat_code', 'intermediate_panchayat_code'],
}
