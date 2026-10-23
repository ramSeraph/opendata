"""Reported record identities; these are not guaranteed foreign keys."""


from .organizations import KEYS as ORGANIZATION_KEYS


ROW_KEYS = {
    **ORGANIZATION_KEYS,
    'nofn_panchayats': ['local_body_code', 'state_code', 'district_name', 'subdistrict_name'],
    'state_orgs': ['organization_code', 'state_code'],
    'central_orgs': ['organization_code'],
    'pincode_villages': ['village_code', 'pincode', 'state_code', 'district_code', 'subdistrict_code'],
    'pincode_urban': ['local_body_code', 'state_code', 'pincode'],
    'invalidated_census_villages': ['village_code', 'state_code'],
    'constituencies_mapping_urban': ['ward_code', 'local_body_code', 'state_code', 'district_code', 'subdistrict_code', 'parliament_constituency_code', 'assembly_constituency_code'],
    'constituencies_mapping_pri': ['village_code', 'local_body_code', 'local_body_name', 'block_code', 'state_code', 'district_code', 'subdistrict_code', 'parliament_constituency_code', 'assembly_constituency_code'],
    'parliament_constituencies_lb_mapping': ['parliament_constituency_code', 'state_code', 'assembly_constituency_name', 'local_body_name', 'local_body_type_name', 'coverage_type'],
    'constituency_coverage': ['entity_code', 'entity_type', 'parliament_constituency_code', 'assembly_constituency_code', 'state_code', 'coverage_type'],
    'parliament_constituencies': ['parliament_constituency_code', 'state_code'],
    'assembly_constituencies': ['assembly_constituency_code', 'parliament_constituency_code', 'state_code'],
    'tlb_villages': ['village_code', 'block_code', 'local_body_code', 'state_code', 'district_code', 'subdistrict_code'],
    'statewise_ulbs_coverage': ['local_body_code', 'district_code', 'subdistrict_code', 'village_code'],
    'district_panchayats': ['district_panchayat_code', 'district_code', 'state_code'],
    'pri_local_body_wards': ['ward_code', 'local_body_code', 'state_code', 'local_body_name', 'district_panchayat_name', 'intermediate_panchayat_name'],
    'urban_local_body_wards': ['ward_code'],
    'villages_by_blocks': ['village_code', 'block_code', 'local_body_code', 'state_code', 'district_code', 'subdistrict_code', 'block_district_code'],
    'gp_mapping': ['village_code', 'local_body_code', 'state_code', 'district_code', 'subdistrict_code'],
    'states': ['state_code'],
    'districts': ['district_code'],
    'subdistricts': ['subdistrict_code'],
    'blocks': ['block_code', 'district_code'],
    'urban_local_bodies': ['local_body_code'],
    'pri_local_bodies': ['local_body_code'],
    'traditional_local_bodies': ['local_body_code', 'district_panchayat_code', 'intermediate_panchayat_code'],
}
