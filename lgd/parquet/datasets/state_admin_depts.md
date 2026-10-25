# state_admin_depts

Despite its filename, this report defines administrative-unit
levels, not a directory of departments. It supplies level codes/names,
a parent administrative reference, state and optional source metadata
about hierarchy, publication and activity. The level code identifies
the record; state remains an attribute.

[state_admin_dept_units](state_admin_dept_units.md) lists the named
administrative units at those levels. Organizations themselves are
in [state_orgs](state_orgs.md). Administrative levels, administrative
units and organization offices use different identifiers and must
not be equated because their names or numbers match.

## Row identity and conversion

Only the first three source fields are required in addition to state
context. Optional DWR metadata, including flags, timestamps and hierarchy
descriptions, remains text. Parent administrative codes can be signed;
no boolean or timestamp interpretation is imposed.

The normalized record key is:

```text
administrative_unit_level_code
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

`state_code` and `state_name` remain attributes. The
identity review
checks all 1,619 retained observations (30 January 2022–19 October 2026):
1,290 historical level codes, each associated with one state, and no simultaneous
collisions under the level code alone. A later reported state change creates
an attribute version of the same level. Simultaneous conflicting state claims
for one level code fail conversion.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

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
| 18 | `state_code` | `VARCHAR` | `State Code` | No |
| 19 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
