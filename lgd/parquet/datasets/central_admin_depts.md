# central_admin_depts

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/central_admin_depts.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

Despite its filename, this report defines central administrative-unit
levels, including named postal levels, rather than listing departments.
It supplies level codes/names, parent administrative references and
optional hierarchy/publication/activity metadata. It has no state
columns.

[central_admin_dept_units](central_admin_dept_units.md) lists named
units belonging to these levels. The separate
[central_orgs](central_orgs.md) and [central_org_units](central_org_units.md)
reports describe organizations and offices; matching names or numbers
do not establish a shared identifier namespace.

## Row identity and conversion

Only the first three source fields are required. Optional DWR metadata,
including flags, timestamps and hierarchy descriptions, remains text.
Parent administrative codes can be signed; no boolean or timestamp
interpretation is imposed.

The reported record key is:

```text
(administrative_unit_level_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `administrative_unit_level_code` | `VARCHAR` | `adminUnitCode` | No |
| 2 | `administrative_unit_level_name` | `VARCHAR` | `adminLevelNameEng` | No |
| 3 | `parent_administrative_code` | `VARCHAR` | `parentAdminCode` | No |
| 4 | `organization_level_code` | `VARCHAR` | `orgLocatedLevelCode` | Yes → NULL |
| 5 | `administrative_unit_level_name_local` | `VARCHAR` | `adminLevelNameLocal` | Yes → NULL |
| 6 | `created_by` | `VARCHAR` | `createdby` | Yes → NULL |
| 7 | `created_on` | `VARCHAR` | `createdon` | Yes → NULL |
| 8 | `hierarchy` | `VARCHAR` | `hierarchy` | Yes → NULL |
| 9 | `is_active` | `VARCHAR` | `isactive` | Yes → NULL |
| 10 | `publication_status` | `VARCHAR` | `ispublish` | Yes → NULL |
| 11 | `local_body_level` | `VARCHAR` | `localBodyLevel` | Yes → NULL |
| 12 | `organization_located_at_levels` | `VARCHAR` | `orgLocatedAtLevels` | Yes → NULL |
| 13 | `overlap_unit` | `VARCHAR` | `overlapUnit` | Yes → NULL |
| 14 | `parent_category` | `VARCHAR` | `parentCategory` | Yes → NULL |
| 15 | `parent_organization_level_code` | `VARCHAR` | `parentOrgLocatedLevelCode` | Yes → NULL |
| 16 | `revenue_entity` | `VARCHAR` | `revenueEntity` | Yes → NULL |
| 17 | `unit_level_type` | `VARCHAR` | `unitLevelType` | Yes → NULL |
