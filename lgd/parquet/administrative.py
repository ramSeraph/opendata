"""Canonicalize one administrative report without keeping observation history."""

from .common import header_key, sql_identifier, sql_string
from .constituencies import DATASETS as CONSTITUENCY_DATASETS, Layout
from .csv_input import report
from .errors import InputRejected
from .keys import ROW_KEYS
from .organizations import SCHEMAS as ORGANIZATION_SCHEMAS, ADMIN_LEVEL_FIELDS
from .schema import schema_id, validate_fields


# The central report has no state fields. Parent ministries can be supplied
# only as references; do not fabricate additional organization rows for them.
ORGANIZATION_FIELDS = (
    (1, 'organization_code', 'VARCHAR', 'Organization Code'),
    (2, 'organization_name', 'VARCHAR', 'Organization Name'),
    (3, 'organization_type', 'VARCHAR', 'Organization Type'),
    (4, 'parent_organization_code', 'VARCHAR', 'Parent Organization Code'),
    (5, 'parent_organization_name', 'VARCHAR', 'Parent Organization Name'),
    (6, 'parent_organization_type', 'VARCHAR', 'Parent Organization Type'),
)

# IDs are stable within each dataset; do not recycle them or derive them from CSV order.
SCHEMAS = {
    **ORGANIZATION_SCHEMAS,
    'nofn_panchayats': (
        (1, 'local_body_code', 'VARCHAR', 'Local Body Code'),
        (2, 'local_body_name', 'VARCHAR', 'Local Body Name (In English)'),
        (3, 'district_name', 'VARCHAR', 'District Name'),
        (4, 'subdistrict_name', 'VARCHAR', 'Sub District Name(In English)'),
        (5, 'state_code', 'VARCHAR', 'State Code'),
        (6, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'state_orgs': ORGANIZATION_FIELDS + (
        (7, 'state_code', 'VARCHAR', 'State Code'),
        (8, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'central_orgs': ORGANIZATION_FIELDS,
    'pincode_villages': (
        (1, 'village_code', 'VARCHAR', 'Village Code'),
        (2, 'village_name', 'VARCHAR', 'Village Name'),
        (3, 'pincode', 'VARCHAR', 'Pincode'),
        (4, 'subdistrict_code', 'VARCHAR', 'Subdistrict Code'),
        (5, 'subdistrict_name', 'VARCHAR', 'Subdistrict Name'),
        (6, 'district_code', 'VARCHAR', 'District Code'),
        (7, 'district_name', 'VARCHAR', 'District Name'),
        (8, 'state_code', 'VARCHAR', 'State Code'),
        (9, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'pincode_urban': (
        (1, 'local_body_code', 'VARCHAR', 'Localbody Code'),
        (2, 'local_body_name', 'VARCHAR', 'Localbody Name'),
        (3, 'local_body_type_name', 'VARCHAR', 'Localbody Type Name'),
        (4, 'pincode', 'VARCHAR', 'Pincode'),
        (5, 'state_code', 'VARCHAR', 'State Code'),
        (6, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'invalidated_census_villages': (
        (1, 'village_code', 'VARCHAR', 'Village Code'),
        (2, 'village_name', 'VARCHAR', 'Village Name(In English)'),
        (3, 'state_code', 'VARCHAR', 'State Code'),
        (4, 'state_name', 'VARCHAR', 'State Name (In English)'),
        (5, 'village_census_2001_code', 'VARCHAR', 'Census Code 2001'),
        (6, 'village_census_2011_code', 'VARCHAR', 'Census Code 2011'),
    ),
    'constituencies_mapping_urban': (
        (1, 'ward_code', 'VARCHAR', 'Ward Code'),
        (2, 'ward_name', 'VARCHAR', 'Ward Name'),
        (3, 'local_body_code', 'VARCHAR', 'Urban Localbody Code'),
        (4, 'local_body_name', 'VARCHAR', 'Urban Localbody Name'),
        (5, 'local_body_type_name', 'VARCHAR', 'Localbody Type'),
        (6, 'parliament_constituency_code', 'VARCHAR', 'Parliament Constituency code'),
        (7, 'parliament_constituency_name', 'VARCHAR', 'Parliament Constituency Name'),
        (8, 'parliament_constituency_eci_code', 'VARCHAR', 'Parliament Constituency ECI Code'),
        (9, 'assembly_constituency_code', 'VARCHAR', 'Assembly Constituency Code'),
        (10, 'assembly_constituency_name', 'VARCHAR', 'Assembly Constituency Name'),
        (11, 'assembly_constituency_eci_code', 'VARCHAR', 'Assembly Constituency ECI Code'),
        (12, 'district_code', 'VARCHAR', 'District Code'),
        (13, 'district_name', 'VARCHAR', 'District Name'),
        (14, 'subdistrict_code', 'VARCHAR', 'Subdistrict Code'),
        (15, 'subdistrict_name', 'VARCHAR', 'Subdistrict Name'),
        (16, 'state_code', 'VARCHAR', 'State Code'),
    ),
    'constituencies_mapping_pri': (
        (1, 'village_code', 'VARCHAR', 'Village Code'),
        (2, 'village_name', 'VARCHAR', 'Village Name'),
        (3, 'village_census_2011_code', 'VARCHAR', 'Village Census 2011 Code'),
        (4, 'local_body_code', 'VARCHAR', 'Rural Localbody Code'),
        (5, 'local_body_name', 'VARCHAR', 'Rural LocalbodyName'),
        (6, 'block_code', 'VARCHAR', 'Block Code'),
        (7, 'block_name', 'VARCHAR', 'Block Name'),
        (8, 'subdistrict_code', 'VARCHAR', 'Subdistrict Code'),
        (9, 'subdistrict_name', 'VARCHAR', 'Subdistrict Name'),
        (10, 'subdistrict_census_2011_code', 'VARCHAR', 'Subdistrict Census 2011 Code'),
        (11, 'district_code', 'VARCHAR', 'District Code'),
        (12, 'district_name', 'VARCHAR', 'District Name'),
        (13, 'district_census_2011_code', 'VARCHAR', 'District Census 2011 Code'),
        (14, 'parliament_constituency_code', 'VARCHAR', 'Parliament Constituency code'),
        (15, 'parliament_constituency_name', 'VARCHAR', 'Parliament Constituency Name'),
        (16, 'parliament_constituency_eci_code', 'VARCHAR', 'Parliament Constituency ECI Code'),
        (17, 'assembly_constituency_code', 'VARCHAR', 'Assembly Constituency Code'),
        (18, 'assembly_constituency_name', 'VARCHAR', 'Assembly Constituency Name'),
        (19, 'assembly_constituency_eci_code', 'VARCHAR', 'Assembly Constituency ECI Code'),
        (20, 'state_code', 'VARCHAR', 'State Code'),
    ),
    'parliament_constituencies_lb_mapping': (
        (1, 'parliament_constituency_code', 'VARCHAR', 'Parliament Constituency Code'),
        (2, 'parliament_constituency_name', 'VARCHAR', 'Parliament'),
        (3, 'assembly_constituency_name', 'VARCHAR', 'Assembly'),
        (4, 'local_body_name', 'VARCHAR', 'Local Gov. Name'),
        (5, 'local_body_type_name', 'VARCHAR', 'Classification'),
        (6, 'coverage_type', 'VARCHAR', 'Coverage'),
        (7, 'state_code', 'VARCHAR', 'State Code'),
    ),
    'constituency_coverage': (
        (1, 'entity_code', 'VARCHAR', 'Entity Code'),
        (2, 'entity_name', 'VARCHAR', 'Entity Name'),
        (3, 'entity_type', 'VARCHAR', 'Entity Type'),
        (4, 'parliament_constituency_code', 'VARCHAR', 'Parliament Constituency Code'),
        (5, 'parliament_constituency_name', 'VARCHAR', 'Parliament Constituency Name'),
        (6, 'assembly_constituency_code', 'VARCHAR', 'Assembly Constituency Code'),
        (7, 'assembly_constituency_name', 'VARCHAR', 'Assembly Constituency Name'),
        (8, 'coverage_type', 'VARCHAR', 'Coverage Type'),
        (9, 'state_code', 'VARCHAR', 'State Code'),
        (10, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'parliament_constituencies': (
        (1, 'parliament_constituency_code', 'VARCHAR', 'Parliament Constituency Code'),
        (2, 'parliament_constituency_name', 'VARCHAR', 'Parliament Constituency Name'),
        (3, 'state_code', 'VARCHAR', 'State Code'),
        (4, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'assembly_constituencies': (
        (1, 'assembly_constituency_code', 'VARCHAR', 'Assembly Constituency Code'),
        (2, 'assembly_constituency_name', 'VARCHAR', 'Assembly Constituency Name'),
        (3, 'parliament_constituency_code', 'VARCHAR', 'Parliament Constituency Code'),
        (4, 'parliament_constituency_name', 'VARCHAR', 'Parliament Constituency Name'),
        (5, 'state_code', 'VARCHAR', 'State Code'),
        (6, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'tlb_villages': (
        (1, 'village_code', 'VARCHAR', 'Village Code'),
        (2, 'village_name', 'VARCHAR', 'Village Name (In English)'),
        (3, 'local_body_code', 'VARCHAR', 'Gram Panchayat/ TLB Code'),
        (4, 'local_body_name', 'VARCHAR', 'Gram Panchayat/ TLB (In English)'),
        (5, 'local_body_type_code', 'VARCHAR', 'Gram Panchayat/ TLB Type Code'),
        (6, 'local_body_type_name', 'VARCHAR', 'Gram Panchayat/ TLB Type Name'),
        (7, 'block_code', 'VARCHAR', 'Block Code'),
        (8, 'block_name', 'VARCHAR', 'Block Name (In English)'),
        (9, 'subdistrict_code', 'VARCHAR', 'Sub-district Code'),
        (10, 'subdistrict_name', 'VARCHAR', 'Sub-district Name (In English)'),
        (11, 'district_code', 'VARCHAR', 'District Code'),
        (12, 'district_name', 'VARCHAR', 'District Name (In English)'),
        (13, 'state_code', 'VARCHAR', 'State Code'),
        (14, 'state_name', 'VARCHAR', 'State Name'),
        (15, 'state_census_2011_code', 'VARCHAR', 'State Census 2011 Code'),
        (16, 'district_census_2011_code', 'VARCHAR', 'District Census 2011 Code'),
        (17, 'subdistrict_census_2011_code', 'VARCHAR', 'Sub-district Census 2011 code'),
        (18, 'village_census_2011_code', 'VARCHAR', 'Village Census 2011 Code'),
        # Retired field ID 19: the source body-census column is ignored.
    ),
    'statewise_ulbs_coverage': (
        (1, 'local_body_code', 'VARCHAR', 'Local Body Code'),
        (2, 'local_body_name', 'VARCHAR', 'Local Body Name (In English)'),
        (3, 'district_code', 'VARCHAR', 'District Code'),
        (4, 'district_name', 'VARCHAR', 'District Name (In English)'),
        (5, 'subdistrict_code', 'VARCHAR', 'Subdistrict Code'),
        (6, 'subdistrict_name', 'VARCHAR', 'Subdistrict Name (In English)'),
        (7, 'village_code', 'VARCHAR', 'Village Code'),
        (8, 'village_name', 'VARCHAR', 'Village Name (In English)'),
        (9, 'state_name', 'VARCHAR', 'State Name (In English)'),
        (10, 'local_body_census_2011_code', 'VARCHAR', 'Census 2011 Code'),
    ),
    'district_panchayats': (
        (1, 'district_panchayat_code', 'VARCHAR', 'District Panchayat Code'),
        (2, 'district_panchayat_name', 'VARCHAR', 'District Panchayat'),
        (3, 'district_code', 'VARCHAR', 'District Code'),
        (4, 'district_name', 'VARCHAR', 'District Name'),
        (5, 'state_code', 'VARCHAR', 'State Code'),
        (6, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'pri_local_body_wards': (
        (1, 'ward_code', 'VARCHAR', 'Ward Code'),
        (2, 'ward_number', 'VARCHAR', 'Ward Number'),
        (3, 'ward_name', 'VARCHAR', 'Ward Name (In English)'),
        (4, 'local_body_code', 'VARCHAR', 'Local Body Code'),
        (5, 'local_body_name', 'VARCHAR', 'Local Body Name'),
        (6, 'state_code', 'VARCHAR', 'State Code'),
        (7, 'state_name', 'VARCHAR', 'State Name'),
        (8, 'ward_name_local', 'VARCHAR', 'Ward Name (In Local)'),
        (9, 'local_body_type_name', 'VARCHAR', 'Local Body Type'),
        (10, 'district_panchayat_name', 'VARCHAR', 'District Level Parent Name'),
        (11, 'intermediate_panchayat_name', 'VARCHAR', 'Intermediate Level Parent Name'),
    ),
    'urban_local_body_wards': (
        (1, 'ward_code', 'VARCHAR', 'Ward Code'),
        (2, 'ward_number', 'VARCHAR', 'Ward Number'),
        (3, 'ward_name', 'VARCHAR', 'Ward Name'),
        (4, 'local_body_code', 'VARCHAR', 'Local Body Code'),
        (5, 'local_body_name', 'VARCHAR', 'Local Body Name'),
        (6, 'state_code', 'VARCHAR', 'State Code'),
        (7, 'state_name', 'VARCHAR', 'State Name'),
        (8, 'local_body_census_2011_code', 'VARCHAR', 'Census 2011 Code'),
    ),
    'villages_by_blocks': (
        (1, 'village_code', 'VARCHAR', 'Village Code'),
        (2, 'village_name', 'VARCHAR', 'Village Name (In English)'),
        (3, 'block_code', 'VARCHAR', 'Development Block Code'),
        (4, 'block_name', 'VARCHAR', 'Development Block Name (In English)'),
        (5, 'local_body_code', 'VARCHAR', 'Local Body Code'),
        (6, 'local_body_name', 'VARCHAR', 'Local Body Name (In English)'),
        (7, 'subdistrict_code', 'VARCHAR', 'Subdistrict Code'),
        (8, 'subdistrict_name', 'VARCHAR', 'Subdistrict Name (In English)'),
        (9, 'district_code', 'VARCHAR', 'District Code'),
        (10, 'district_name', 'VARCHAR', 'District Name (In English)'),
        (11, 'state_code', 'VARCHAR', 'State Code'),
        (12, 'state_name', 'VARCHAR', 'State Name (In English)'),
        (13, 'village_census_2011_code', 'VARCHAR', 'Village Census 2011 Code'),
        (14, 'subdistrict_census_2011_code', 'VARCHAR', 'Subdistrict Census 2011 Code'),
        (15, 'district_census_2011_code', 'VARCHAR', 'District Census 2011 Code'),
        (16, 'state_census_2011_code', 'VARCHAR', 'State Census 2011 Code'),
        (17, 'local_body_census_2011_code', 'VARCHAR', 'Local Body 2011 Code'),
        # Retired field IDs 18/19: block districts belong in the blocks dataset.
        # Their source headers are still recognized and recorded as provenance.
    ),
    'gp_mapping': (
        (1, 'village_code', 'VARCHAR', 'Village Code'),
        (2, 'village_name', 'VARCHAR', 'Village Name (in English)'),
        (3, 'local_body_code', 'VARCHAR', 'Local Body Code'),
        (4, 'local_body_name', 'VARCHAR', 'Local Body Name (in English)'),
        (5, 'subdistrict_code', 'VARCHAR', 'Subdistrict Code'),
        (6, 'subdistrict_name', 'VARCHAR', 'Subdistrict Name (in English)'),
        (7, 'district_code', 'VARCHAR', 'District Code'),
        (8, 'district_name', 'VARCHAR', 'District Name (in English)'),
        (9, 'state_code', 'VARCHAR', 'State Code'),
        (10, 'state_name', 'VARCHAR', 'State Name'),
        (11, 'village_census_2011_code', 'VARCHAR', 'Village Census 2011 Code'),
        (12, 'village_census_2001_code', 'VARCHAR', 'Village Census 2001 Code'),
        (13, 'subdistrict_census_2011_code', 'VARCHAR', 'Subdistrict Census Code 2011'),
        (14, 'subdistrict_census_2001_code', 'VARCHAR', 'Subdistrict Census Code 2001'),
        (15, 'district_census_2011_code', 'VARCHAR', 'District Census 2011 Code'),
        (16, 'district_census_2001_code', 'VARCHAR', 'District Census 2001 Code'),
    ),
    'states': (
        (1, 'state_code', 'VARCHAR', 'State Code'),
        (2, 'state_version', 'INTEGER', 'State Version'),
        (3, 'state_name', 'VARCHAR', 'State Name (In English)'),
        (4, 'state_name_local', 'VARCHAR', 'State Name (In Local)'),
        (5, 'state_census_2001_code', 'VARCHAR', 'Census 2001 Code'),
        (6, 'state_census_2011_code', 'VARCHAR', 'Census 2011 Code'),
        (7, 'state_or_ut', 'VARCHAR', 'State or UT'),
    ),
    'districts': (
        (1, 'district_code', 'VARCHAR', 'District Code'),
        (2, 'district_name', 'VARCHAR', 'District Name (In English)'),
        (3, 'state_code', 'VARCHAR', 'State Code'),
        (4, 'state_name', 'VARCHAR', 'State Name (In English)'),
        (5, 'district_census_2001_code', 'VARCHAR', 'Census 2001 Code'),
        (6, 'district_census_2011_code', 'VARCHAR', 'Census 2011 Code'),
    ),
    'subdistricts': (
        (1, 'subdistrict_code', 'VARCHAR', 'Sub-district Code'),
        (2, 'subdistrict_version', 'INTEGER', 'Sub-district Version'),
        (3, 'subdistrict_name', 'VARCHAR', 'Sub-district Name'),
        (4, 'district_code', 'VARCHAR', 'District Code'),
        (5, 'district_name', 'VARCHAR', 'District Name'),
        (6, 'state_code', 'VARCHAR', 'State Code'),
        (7, 'state_name', 'VARCHAR', 'State Name'),
        (8, 'subdistrict_census_2001_code', 'VARCHAR', 'Census 2001 Code'),
        (9, 'subdistrict_census_2011_code', 'VARCHAR', 'Census 2011 Code'),
    ),
    'blocks': (
        (1, 'block_code', 'VARCHAR', 'Block Code'),
        (2, 'block_version', 'INTEGER', 'Block Version'),
        (3, 'block_name', 'VARCHAR', 'Block Name (In English)'),
        (4, 'block_name_local', 'VARCHAR', 'Block Name (In Local)'),
        (5, 'district_code', 'VARCHAR', 'District Code'),
        (6, 'district_name', 'VARCHAR', 'District Name (In English)'),
        (7, 'state_code', 'VARCHAR', 'State Code'),
        (8, 'state_name', 'VARCHAR', 'State Name (In English)'),
    ),
    'urban_local_bodies': (
        (1, 'local_body_code', 'VARCHAR', 'Local Body Code'),
        (2, 'local_body_version', 'INTEGER', 'Local Body Version'),
        (3, 'local_body_name', 'VARCHAR', 'Local Body Name (In English)'),
        (4, 'local_body_name_local', 'VARCHAR', 'Local Body Name (In Local)'),
        (5, 'local_body_type_code', 'VARCHAR', 'Localbody Type Code'),
        (6, 'local_body_census_2011_code', 'VARCHAR', 'Census 2011 Code'),
        (7, 'state_code', 'VARCHAR', 'State Code'),
        (8, 'state_name', 'VARCHAR', 'State Name (In English)'),
    ),
    'pri_local_bodies': (
        (1, 'local_body_code', 'VARCHAR', 'Localbody Code'),
        (2, 'local_body_version', 'INTEGER', 'Localbody Version'),
        (3, 'local_body_name', 'VARCHAR', 'Localbody Name (In English)'),
        (4, 'local_body_name_local', 'VARCHAR', 'Localbody Name (In Local)'),
        (5, 'local_body_type_code', 'VARCHAR', 'Localbody Type Code'),
        (6, 'local_body_type_name', 'VARCHAR', 'Localbody Type Name'),
        (7, 'parent_local_body_code', 'VARCHAR', 'Parent Localbody Code'),
        (8, 'state_code', 'VARCHAR', 'State Code'),
        (9, 'state_name', 'VARCHAR', 'State Name'),
    ),
    'traditional_local_bodies': (
        (1, 'local_body_code', 'VARCHAR', 'Localbody Code'),
        (2, 'local_body_version', 'INTEGER', 'Localbody Version'),
        (3, 'local_body_name', 'VARCHAR', 'Localbody Name (In English)'),
        (4, 'local_body_name_local', 'VARCHAR', 'Localbody Name (In Local)'),
        (5, 'local_body_type_code', 'VARCHAR', 'Localbody Type Code'),
        (6, 'local_body_type_name', 'VARCHAR', 'Localbody Type Name'),
        (7, 'district_panchayat_code', 'VARCHAR', 'District Panchayat Code'),
        (8, 'intermediate_panchayat_code', 'VARCHAR', 'Intermediate/Block Panchayat Code'),
        (9, 'state_code', 'VARCHAR', 'State Code'),
        (10, 'state_name', 'VARCHAR', 'State Name (In English)'),
        (11, 'local_body_level', 'VARCHAR', 'Local Body Level'),
    ),
}

# Additive IDs avoid the already published history metadata IDs (11–13 and
# 21–23 respectively). None marks a derived field, never a source header.
for _dataset, _first_id in (('constituency_coverage', 14), ('constituencies_mapping_pri', 24)):
    SCHEMAS[_dataset] += ((_first_id, 'constituency_level', 'VARCHAR', None),
                         (_first_id+1, 'constituency_code', 'VARCHAR', None))


class AdministrativeReport:
    def __init__(self, dataset):
        self.dataset = dataset
        self.fields = SCHEMAS[dataset]
        self.columns = [name for _, name, _, _ in self.fields]
        self.identity = self.columns[0]
        self.key_columns = ROW_KEYS[dataset].copy()
        self.version = next((name for _, name, kind, _ in self.fields if kind == 'INTEGER'), None)
        self.derived = {name for _, name, _, header in self.fields if header is None}
        self.aliases = {header_key(header): name for _, name, _, header in self.fields if header is not None}
        if dataset == 'invalidated_census_villages':
            self.aliases.update({header_key(header): name for header, name in (
                ('State LGD Code', 'state_code'), ('Village LGD Code', 'village_code'),
                ('State Name English', 'state_name'), ('Village Name English', 'village_name'),
            )})
        if dataset == 'tlb_villages':
            self.aliases.update({header_key(header): name for header, name in (
                ('State Name (In English)', 'state_name'),
                ('Local Body Code', 'local_body_code'),
                ('Local Body Name (In English)', 'local_body_name'),
                # Recognize the retired field for raw-header provenance only.
                ('Gram Panchayat/ TLB Census 2011 Code', 'local_body_census_2011_code'),
                ('Local Body 2011 Code', 'local_body_census_2011_code'),
                ('Development Block Code', 'block_code'),
                ('Development Block Name (In English)', 'block_name'),
            )})
        if dataset == 'district_panchayats':
            self.aliases[header_key('Disrict Code')] = 'district_code'
            self.aliases[header_key('State Name (In English)')] = 'state_name'
        if dataset == 'pri_local_body_wards':
            self.aliases.update({header_key(header): name for header, name in (
                ('Localbody Name (In English)', 'local_body_name'),
                ('Disrtict Level Parent Name', 'district_panchayat_name'),
                ('Word Code', 'ward_code'), ('Word Number', 'ward_number'),
            )})
        if dataset == 'urban_local_body_wards':
            self.aliases[header_key('Census Code 2011')] = 'local_body_census_2011_code'
        if dataset == 'blocks':
            self.aliases.update({header_key('Development ' + header): name
                                 for _, name, _, header in self.fields if name.startswith('block_')})
        if dataset in ('urban_local_bodies', 'traditional_local_bodies'):
            self.aliases[header_key('State Name')] = 'state_name'
        if dataset == 'gp_mapping':
            for entity in ('Village', 'Subdistrict', 'District'):
                for year in (2001, 2011):
                    name = f'{entity.lower()}_census_{year}_code'
                    for header in (f'{entity} Census Code {year}', f'{entity} Census {year} Code'):
                        self.aliases[header_key(header)] = name
        if dataset == 'villages_by_blocks':
            for entity in ('Village', 'Subdistrict', 'District', 'State', 'Local Body'):
                stem = entity.lower().replace(' ', '_')
                self.aliases[header_key(f'{entity} Name')] = f'{stem}_name'
                for header in (f'{entity} Census Code', f'{entity} Census Code 2011',
                               f'{entity} Census 2011 Code'):
                    self.aliases[header_key(header)] = f'{stem}_census_2011_code'
            self.aliases[header_key('VillageCunsecCode')] = 'village_census_2011_code'
            for prefix in ('Block', 'Development Block'):
                self.aliases[header_key(f'{prefix} Code')] = 'block_code'
                for suffix in ('', ' (In English)'):
                    self.aliases[header_key(f'{prefix} Name{suffix}')] = 'block_name'
                    self.aliases[header_key(f'District Name of {prefix}{suffix}')] = 'block_district_name'
                self.aliases[header_key(f'District Code of {prefix}')] = 'block_district_code'
        self.optional = {'state_name_local'} if dataset == 'states' else set()
        if dataset in ('state_admin_depts', 'central_admin_depts'):
            self.optional = {f[1] for f in ADMIN_LEVEL_FIELDS[3:]}
        if dataset == 'invalidated_census_villages':
            self.optional = {'village_census_2001_code', 'village_census_2011_code'}
        if dataset == 'tlb_villages':
            self.optional = {'local_body_type_code', 'local_body_type_name'}
        if dataset == 'urban_local_body_wards':
            self.optional = {'local_body_census_2011_code'}
        # Top-level PRI bodies legitimately have no reported parent. Keep the
        # supplied empty string; do not invent a parent or conflate it with NULL.
        self.blank_codes = {'parent_local_body_code'} if dataset == 'pri_local_bodies' else set()
        self.signed_codes = set()
        self.text_codes = set()
        if dataset in ORGANIZATION_SCHEMAS:
            self.blank_codes = {'organization_level_code', 'parent_organization_level_code',
                                'parent_organization_unit_code'}
            self.signed_codes = {'entity_code', 'parent_administrative_code'}
        if dataset == 'org_unit_details':
            self.blank_codes = set()
            self.signed_codes = {'entity_type'}
            # Organization-specific identifiers include SWD, HO and OMP BO.
            self.text_codes = {'organization_unit_specific_code'}
        if dataset in ('state_orgs', 'central_orgs'):
            self.blank_codes = {'parent_organization_code'}
        if dataset == 'invalidated_census_villages':
            self.blank_codes = {'village_code'}
        if dataset in ('assembly_constituencies', 'constituency_coverage'):
            self.blank_codes = {'assembly_constituency_code'}
        if dataset in ('constituencies_mapping_urban', 'constituencies_mapping_pri'):
            self.blank_codes = {'assembly_constituency_code', 'assembly_constituency_eci_code',
                                'parliament_constituency_eci_code'}
            self.blank_codes.update({'district_code', 'subdistrict_code'}
                                    if dataset.endswith('urban') else {'local_body_code', 'block_code'})
        if dataset == 'tlb_villages':
            self.blank_codes = {'village_code', 'subdistrict_code', 'block_code',
                                'local_body_code', 'local_body_type_code'}
        if dataset == 'statewise_ulbs_coverage':
            self.blank_codes = {'district_code', 'subdistrict_code', 'village_code'}
        if dataset == 'gp_mapping':
            self.blank_codes = {'local_body_code', 'village_code', 'subdistrict_code'}
        if dataset == 'villages_by_blocks':
            self.optional = {'local_body_code', 'local_body_name', 'local_body_census_2011_code'}
            self.blank_codes = {'local_body_code', 'village_code', 'subdistrict_code',
                                'block_code'}
        self.embedded_header_rows = 0
        if dataset == 'traditional_local_bodies':
            self.optional = {'local_body_version', 'local_body_name_local',
                             'local_body_type_code', 'local_body_type_name', 'local_body_level'}
            self.blank_codes = {'local_body_type_code', 'district_panchayat_code',
                                'intermediate_panchayat_code'}
        validate_fields(dataset, self.fields)

    def map_headers(self, headers):
        mapping, seen = {}, set()
        for header in headers:
            key = header_key(header)
            if key in seen:
                raise ValueError(f'Duplicate source column: {header!r}')
            seen.add(key)
            if key == header_key('S.No.'):
                continue
            if self.dataset == 'nofn_panchayats' and key == header_key('SR.NO'):
                continue
            if self.dataset == 'invalidated_census_villages' and key == header_key('Sr No.'):
                continue
            if self.dataset == 'constituency_coverage' and key == header_key('State Name English'):
                # A historical layout adds this empty column beside State Name.
                # load_source checks every raw value before ignoring it.
                continue
            if self.dataset == 'parliament_constituencies' and key in (
                    header_key('Assembly Constituency Code'), header_key('Assembly Constituency Name')):
                # The PC export shares the AC header. Check these raw columns
                # are empty before dropping them from the canonical PC schema.
                continue
            name = self.aliases.get(key)
            if name is None:
                raise ValueError(f'Unknown {self.dataset} column: {header!r}')
            if name in mapping:
                if self.dataset == 'tlb_villages' and name == 'state_name':
                    # The newer export contains both name headers. Values are
                    # checked for exact agreement after reading the CSV.
                    if key == header_key('State Name (In English)'):
                        mapping[name] = header
                    continue
                raise ValueError(f'Multiple source columns map to {name}')
            mapping[name] = header
        missing = set(self.columns) - self.optional - self.derived - mapping.keys()
        if missing:
            raise ValueError(f'Missing required {self.dataset} columns: {sorted(missing)}')
        if self.dataset == 'tlb_villages' and 0 < len(self.optional & mapping.keys()) < len(self.optional):
            raise ValueError('Local-body type code and name must be supplied together')
        if self.dataset == 'villages_by_blocks':
            for group in ({'block_district_code', 'block_district_name'},
                          {'local_body_code', 'local_body_name', 'local_body_census_2011_code'}):
                if 0 < len(group & mapping.keys()) < len(group):
                    raise ValueError(f'Columns must be supplied together: {sorted(group)}')
        if self.dataset == 'traditional_local_bodies' and not (
                {'local_body_type_code', 'local_body_level'} & mapping.keys()):
            raise ValueError('Traditional local bodies must supply a type code or level column')
        return mapping, schema_id(mapping)

    def load_source(self, connection, path, *, observed_on=None):
        with report(path) as source:
            headers = source.headers
            mapping, schema_id = self.map_headers(headers)
            layout = Layout(headers) if self.dataset in CONSTITUENCY_DATASETS else None
            source.load(connection, 'entity_source', observe=layout.observe if layout else None)
            if layout:
                self.constituency_layout = layout.result()
        if self.dataset in CONSTITUENCY_DATASETS:
            # Layout validated the full literal timestamp signature and
            # empty remaining cells. No arbitrary malformed row is discarded.
            connection.execute('''DELETE FROM entity_source
                WHERE NOT regexp_full_match("S.No.", '[0-9]+')''')
        if self.dataset == 'parliament_constituencies':
            extra = [h for h in headers if header_key(h) in (
                header_key('Assembly Constituency Code'), header_key('Assembly Constituency Name'))]
            if len(extra) == 1:
                raise ValueError('Assembly code and name columns must be supplied together')
            if extra and connection.execute('SELECT count(*) FROM entity_source WHERE ' +
                    ' OR '.join(f"{sql_identifier(h)}!=''" for h in extra)).fetchone()[0]:
                raise ValueError('Parliament report unexpectedly supplies assembly data')
        if self.dataset == 'constituency_coverage':
            extra = [h for h in headers if header_key(h) == header_key('State Name English')]
            if extra and connection.execute('SELECT count(*) FROM entity_source WHERE ' +
                    ' OR '.join(f"{sql_identifier(h)}!=''" for h in extra)).fetchone()[0]:
                raise ValueError('Constituency coverage unexpectedly supplies State Name English')
        if self.dataset == 'tlb_villages':
            names = [h for h in headers if self.aliases.get(header_key(h)) == 'state_name']
            if len(names) == 2:
                different = connection.execute(f'''SELECT count(*) FROM entity_source
                    WHERE {sql_identifier(names[0])} IS DISTINCT FROM {sql_identifier(names[1])}''').fetchone()[0]
                if different:
                    raise ValueError(f'tlb_villages: {different} rows have conflicting state-name columns')
        self.embedded_header_rows = 0
        if self.dataset == 'villages_by_blocks':
            # Some exports repeat the second line of a split header per state.
            # Remove only the complete literal signature, never arbitrary rows
            # with empty codes. The observation records how many were removed.
            names = {h for n, h in mapping.items() if n.endswith('_name')}
            signature = ' AND '.join(f'{sql_identifier(h)}={sql_string("(In English)" if h in names else "")}'
                                     for h in headers)
            self.embedded_header_rows = connection.execute(
                f'SELECT count(*) FROM entity_source WHERE {signature}').fetchone()[0]
            connection.execute(f'DELETE FROM entity_source WHERE {signature}')
        expressions = []
        for _, name, kind, _ in self.fields:
            expression = sql_identifier(mapping[name]) if name in mapping else 'NULL'
            if kind == 'INTEGER':
                invalid = connection.execute(f'''SELECT {expression} FROM entity_source
                    WHERE {expression} != '' AND (NOT regexp_full_match({expression}, '[0-9]+')
                    OR try_cast({expression} AS INTEGER) IS NULL) LIMIT 1''').fetchone()
                if invalid:
                    raise ValueError(f'Invalid {name}: {invalid[0]!r}')
                expression = f'CAST(nullif({expression}, \'\') AS INTEGER)'
            else:
                expression = f'CAST({expression} AS VARCHAR)'
            expressions.append(f'{expression} AS {name}')
        connection.execute(f'''CREATE OR REPLACE TEMP TABLE entity_incoming AS
            SELECT {', '.join(expressions)}, ?::VARCHAR AS source_schema_id FROM entity_source''', [schema_id])
        if self.derived:
            from .constituency_identity import add_identity
            add_identity(connection)
        count = connection.execute('SELECT count(*) FROM entity_incoming').fetchone()[0]
        self.source_row_count = count
        # Only the count is needed after canonicalization. Releasing the raw
        # CSV table avoids keeping two national reports in memory/spill files.
        connection.execute('DROP TABLE entity_source')
        if count == 0:
            raise ValueError(f'An empty national {self.dataset} export cannot establish completeness')
        codes = [c for c in self.columns if c.endswith('_code')
                 and c not in self.text_codes
                 and not (c.startswith('census_') or '_census_' in c)]
        if self.dataset == 'org_unit_details':
            codes.append('entity_type')
        invalid_codes = [f"({c} IS NULL OR NOT regexp_full_match({c}, '[0-9]+'))"
                         if c not in self.blank_codes else
                         f"({c} IS NOT NULL AND {c} != '' AND NOT regexp_full_match({c}, '[0-9]+'))"
                         for c in codes]
        for index, code in enumerate(codes):
            if code in self.signed_codes:
                invalid_codes[index] = invalid_codes[index].replace('[0-9]+', '-?[0-9]+')
        if self.dataset == 'gp_mapping':
            # Patkhauli's 24 March 2025 report supplies a newline instead of
            # an empty body code. Preserve it verbatim as an unreported body,
            # only when the corresponding name is also empty.
            index = codes.index('local_body_code')
            invalid_codes[index] = (f"({invalid_codes[index]} AND NOT "
                "(regexp_full_match(local_body_code, '[[:space:]]+') AND local_body_name=''))")
        invalid = connection.execute(f'''SELECT {', '.join(codes)} FROM entity_incoming
            WHERE {' OR '.join(invalid_codes)} LIMIT 1''').fetchone()
        if invalid:
            raise ValueError(f'Invalid {self.dataset} identity: {invalid}')
        if self.dataset == 'assembly_constituencies':
            invalid = connection.execute('''SELECT parliament_constituency_code FROM entity_incoming
                WHERE assembly_constituency_code='' AND assembly_constituency_name!='' LIMIT 1''').fetchone()
            if invalid:
                raise ValueError(f'Invalid assembly placeholder: {invalid}')
        if self.dataset == 'invalidated_census_villages':
            attrs = [n for n in self.columns if n not in ('state_code', 'village_code')]
            populated = ' OR '.join(f"coalesce({n}, '')!=''" for n in attrs)
            if connection.execute(f"SELECT count(*) FROM entity_incoming WHERE village_code='' AND ({populated})").fetchone()[0]:
                raise ValueError('Invalidated-village placeholder has populated attributes')
        if self.dataset == 'constituency_coverage':
            invalid = connection.execute('''SELECT entity_type, coverage_type,
                assembly_constituency_code, assembly_constituency_name FROM entity_incoming
                WHERE entity_type NOT IN ('District', 'SubDistrict', 'Village', 'Localbody', 'Ward')
                   OR coverage_type NOT IN ('Fully Covered', 'Partly Covered')
                   OR (assembly_constituency_code IN ('', '0') AND assembly_constituency_name!='')
                LIMIT 1''').fetchone()
            if invalid:
                raise ValueError(f'Unrecognized constituency coverage values: {invalid}')
        if self.dataset == 'statewise_ulbs_coverage':
            invalid = connection.execute('''SELECT local_body_code,subdistrict_code,village_code
                FROM entity_incoming WHERE trim(state_name)=''
                OR (village_code IN ('', '0') AND village_name!='')
                OR (subdistrict_code IN ('', '0')
                    AND (subdistrict_name!='' OR village_code NOT IN ('', '0')))
                OR (district_code IN ('', '0')
                    AND (district_name!='' OR subdistrict_code NOT IN ('', '0')))
                LIMIT 1''').fetchone()
            if invalid:
                raise ValueError(f'Invalid statewise_ulbs_coverage hierarchy: {invalid}')
        if self.dataset == 'gp_mapping':
            invalid = connection.execute('''SELECT village_code, village_name, subdistrict_code
                FROM entity_incoming WHERE
                (village_code='' AND (village_name!='' OR village_census_2001_code!=''
                                     OR village_census_2011_code!=''))
                OR (subdistrict_code='' AND (village_code!='' OR subdistrict_name!=''))
                LIMIT 1''').fetchone()
            if invalid:
                raise ValueError(f'Invalid gp_mapping placeholder: {invalid}')
        if self.dataset in ('tlb_villages', 'villages_by_blocks'):
            invalid = connection.execute('''SELECT village_code, village_name, subdistrict_code
                FROM entity_incoming WHERE
                (village_code='' AND (village_name!='' OR village_census_2011_code!=''))
                OR (subdistrict_code='' AND (village_code!='' OR subdistrict_name!=''))
                OR (block_code='' AND block_name!='')
                OR (local_body_code='' AND local_body_name!='') LIMIT 1''').fetchone()
            if invalid:
                raise ValueError(f'Invalid {self.dataset} placeholder: {invalid}')
        self.ignored_source_rows = 0
        if self.dataset == 'assembly_constituencies':
            # The report also lists parliamentary seats with no assembly entry.
            # Keep their state coverage signal, but not blank assembly entities.
            connection.execute("""CREATE OR REPLACE TEMP TABLE entity_placeholders AS
                SELECT * FROM entity_incoming WHERE assembly_constituency_code=''""")
            self.ignored_source_rows = connection.execute('SELECT count(*) FROM entity_placeholders').fetchone()[0]
            connection.execute("DELETE FROM entity_incoming WHERE assembly_constituency_code=''")
            count -= self.ignored_source_rows
            if not count:
                raise ValueError('An assembly report with no assembly rows cannot establish completeness')
        if self.dataset == 'gp_mapping':
            # Retain the source's empty-section signal for history coverage,
            # but do not publish hierarchy headings as village/body records.
            invalid = connection.execute("""SELECT state_code, district_code FROM entity_incoming
                WHERE village_code='' AND (local_body_name!='' OR
                    NOT (local_body_code='0' OR regexp_full_match(local_body_code, '[[:space:]]*')))
                LIMIT 1""").fetchone()
            if invalid:
                raise ValueError(f'Invalid gp_mapping placeholder with a populated local body: {invalid}')
            connection.execute("""CREATE OR REPLACE TEMP TABLE entity_placeholders AS
                SELECT * FROM entity_incoming WHERE village_code=''""")
            self.ignored_source_rows = connection.execute('SELECT count(*) FROM entity_placeholders').fetchone()[0]
            connection.execute("DELETE FROM entity_incoming WHERE village_code=''")
            count -= self.ignored_source_rows
            if not count:
                raise ValueError('A gp_mapping report with no village rows cannot establish completeness')
        if self.dataset == 'pri_local_body_wards':
            from .pri_wards import resolve
            reference_available = bool(connection.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name='pri_ward_reference'").fetchone()[0]
                or connection.execute("SELECT count(*) FROM duckdb_views() WHERE view_name='pri_ward_reference'").fetchone()[0])
            self.ward_resolution = resolve(connection, self.columns, observed_on=observed_on,
                                           reference_available=reference_available)
            self.ignored_source_rows = self.ward_resolution['ignored_source_rows']
            self.unresolved_source_rows = self.ward_resolution['unresolved_source_rows']
            count = connection.execute('SELECT count(*) FROM entity_incoming').fetchone()[0]
        if self.dataset == 'constituency_coverage':
            from .constituency_coverage import normalize
            self.conflicting_coverage_rows = normalize(connection, self.key_columns)
            count = connection.execute('SELECT count(*) FROM entity_incoming').fetchone()[0]
        if self.dataset == 'constituencies_mapping_pri':
            from .constituency_identity import normalize_pri_names
            self.conflicting_name_rows = normalize_pri_names(connection, self.key_columns)
        if self.dataset == 'parliament_constituencies_lb_mapping':
            from .parliament_body_coverage import normalize
            self.conflicting_coverage_rows = normalize(connection, self.key_columns)
            count = connection.execute('SELECT count(*) FROM entity_incoming').fetchone()[0]
        keys = ', '.join(self.key_columns)
        # Distinct hashes prove distinct keys (collisions only make this fast
        # path decline). Most large ward reports have no redundant path rows;
        # avoid sorting/grouping every text attribute twice in that case.
        unique_keys = connection.execute(f'''SELECT count(*)=count(DISTINCT hash({keys}))
            FROM entity_incoming''').fetchone()[0]
        if unique_keys:
            return headers, mapping, schema_id, count
        exclusion = f' EXCLUDE ({self.version})' if self.version else ''
        conflicts = connection.execute(f'''SELECT {keys} FROM
            (SELECT DISTINCT *{exclusion} FROM entity_incoming)
            GROUP BY {keys} HAVING count(*) > 1 LIMIT 5''').fetchall()
        if conflicts:
            raise InputRejected(f'Duplicate {self.dataset} codes have conflicting attributes: {conflicts}',
                                affected_keys=[dict(zip(self.key_columns, row)) for row in conflicts])
        if self.version:
            unknown = connection.execute(f'''SELECT {keys} FROM entity_incoming GROUP BY {keys}
                HAVING count({self.version}) > 0 AND count({self.version}) < count(*) LIMIT 5''').fetchall()
            if unknown:
                raise InputRejected(f'Cannot choose the highest unknown {self.dataset} version: {unknown}',
                                    affected_keys=[dict(zip(self.key_columns, row)) for row in unknown])
        order = self.version or keys
        connection.execute(f'''CREATE OR REPLACE TEMP TABLE entity_incoming AS
            SELECT * FROM entity_incoming QUALIFY row_number() OVER
                (PARTITION BY {keys} ORDER BY {order} DESC)=1''')
        count = connection.execute('SELECT count(*) FROM entity_incoming').fetchone()[0]
        return headers, mapping, schema_id, count
