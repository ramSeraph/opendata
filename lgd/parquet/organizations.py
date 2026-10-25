"""Source schemas and record identities for organization reports."""


UNIT_FIELDS = (
    (1, 'organization_unit_code', 'VARCHAR', 'Org Unit Code'),
    (2, 'organization_unit_name', 'VARCHAR', 'Org Unit Name (In English)'),
    (3, 'organization_unit_name_local', 'VARCHAR', 'Org Unit Name (In Local)'),
    (4, 'entity_type', 'VARCHAR', 'Entity Type'),
    (5, 'entity_code', 'VARCHAR', 'Entity Lc'),
    (6, 'parent_organization_unit_code', 'VARCHAR', 'Parent Org Unit Code'),
    (7, 'parent_organization_unit_name', 'VARCHAR', 'Parent Org Unit Name'),
    (8, 'organization_level_code', 'VARCHAR', 'Org Located Level Code'),
    (9, 'organization_code', 'VARCHAR', 'Base Organization Code'),
    (10, 'organization_name', 'VARCHAR', 'Base Organization Name'),
)
DESIGNATION_FIELDS = (
    (1, 'designation_code', 'VARCHAR', 'Designation Code'),
    (2, 'designation_name', 'VARCHAR', 'Designation Name (In English)'),
    (3, 'designation_name_local', 'VARCHAR', 'Designation Name Local (In Local)'),
    (4, 'organization_level_code', 'VARCHAR', 'Org Located Level Code'),
    (5, 'organization_level_name', 'VARCHAR', 'Org Level Specific Name'),
    (6, 'organization_code', 'VARCHAR', 'Base Organization Code'),
    (7, 'organization_name', 'VARCHAR', 'Base Organization Name'),
)
# These reports call the levels "departments", but their values include Branch,
# Division and Post Office. Keep the distinction from organizations and units.
ADMIN_LEVEL_FIELDS = (
    (1, 'administrative_unit_level_code', 'VARCHAR', 'adminUnitCode'),
    (2, 'administrative_unit_level_name', 'VARCHAR', 'adminLevelNameEng'),
    (3, 'parent_administrative_code', 'VARCHAR', 'parentAdminCode'),
    (4, 'organization_level_code', 'VARCHAR', 'orgLocatedLevelCode'),
    (5, 'administrative_unit_level_name_local', 'VARCHAR', 'adminLevelNameLocal'),
    (6, 'created_by', 'VARCHAR', 'createdby'),
    (7, 'created_on', 'VARCHAR', 'createdon'),
    (8, 'hierarchy', 'VARCHAR', 'hierarchy'),
    (9, 'is_active', 'VARCHAR', 'isactive'),
    (10, 'publication_status', 'VARCHAR', 'ispublish'),
    (11, 'local_body_level', 'VARCHAR', 'localBodyLevel'),
    (12, 'organization_located_at_levels', 'VARCHAR', 'orgLocatedAtLevels'),
    (13, 'overlap_unit', 'VARCHAR', 'overlapUnit'),
    (14, 'parent_category', 'VARCHAR', 'parentCategory'),
    (15, 'parent_organization_level_code', 'VARCHAR', 'parentOrgLocatedLevelCode'),
    (16, 'revenue_entity', 'VARCHAR', 'revenueEntity'),
    (17, 'unit_level_type', 'VARCHAR', 'unitLevelType'),
)
ADMIN_UNIT_FIELDS = (
    (1, 'administrative_unit_code', 'VARCHAR', 'Admin Unit Entity Code'),
    (2, 'administrative_unit_name', 'VARCHAR', 'Admin Unit Entity Name'),
    (3, 'administrative_unit_name_local', 'VARCHAR', 'Admin Unit Entity Name (Local)'),
    (4, 'administrative_unit_level_code', 'VARCHAR', 'Admin Department Code'),
    (5, 'administrative_unit_level_name', 'VARCHAR', 'Admin Department Name'),
)
DETAIL_FIELDS = (
    (1, 'organization_unit_code', 'VARCHAR', 'Org Unit Code'),
    (2, 'organization_unit_name', 'VARCHAR', 'Org Unit Name (In English)'),
    (3, 'parent_organization_unit_code', 'VARCHAR', 'Parent Org Unit Code'),
    (4, 'parent_organization_unit_name', 'VARCHAR', 'Parent Org Unit Name'),
    (5, 'organization_unit_specific_code', 'VARCHAR', 'Org Specific Code'),
    (6, 'organization_unit_email', 'VARCHAR', 'Organization Email ID'),
    (7, 'organization_unit_contact_number', 'VARCHAR', 'Organization Contact Number'),
    (8, 'organization_unit_address', 'VARCHAR', 'Organization Address'),
    (9, 'entity_type', 'VARCHAR', 'Entity Type'),
    (10, 'entity_type_name', 'VARCHAR', 'Entity Type Name'),
    (11, 'entity_code', 'VARCHAR', 'Entity Code'),
    (12, 'entity_name', 'VARCHAR', 'Entity Name'),
    (13, 'organization_code', 'VARCHAR', 'Base Organization Code'),
    (14, 'organization_name', 'VARCHAR', 'Base Organization Name'),
    (15, 'state_code', 'VARCHAR', 'State Code'),
    (16, 'state_name', 'VARCHAR', 'State Name'),
)
SCHEMAS = {}
for kind, fields in (('org_units', UNIT_FIELDS), ('org_designations', DESIGNATION_FIELDS),
                     ('admin_depts', ADMIN_LEVEL_FIELDS), ('admin_dept_units', ADMIN_UNIT_FIELDS)):
    SCHEMAS['central_' + kind] = fields
    SCHEMAS['state_' + kind] = fields + (
        (len(fields)+1, 'state_code', 'VARCHAR', 'State Code'),
        (len(fields)+2, 'state_name', 'VARCHAR', 'State Name'),
    )
SCHEMAS['org_unit_details'] = DETAIL_FIELDS
DESIGNATIONS = ('state_org_designations', 'central_org_designations')
STATE_DATASETS = tuple(d for d in SCHEMAS if d.startswith('state_'))
# All entity registers use their own LGD identifier. Designations retain
# distinct organization-level assignments, including differing level names.
KEYS = {dataset: [fields[0][1]] for dataset, fields in SCHEMAS.items()}
for dataset in DESIGNATIONS:
    KEYS[dataset] = ['designation_code', 'organization_level_code', 'organization_level_name']
