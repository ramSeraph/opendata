# state_admin_depts

One reported administrative-unit level. The source calls this a department report, but the levels include Branch, Division and Post Office. Only the first three source fields are required; optional DWR metadata retains strings, including flags, timestamps and hierarchy descriptions. Parent administrative codes can be signed. No boolean or timestamp interpretation is imposed. State codes are part of the identity.

## Row identity and conversion

The reported record key is:

```text
(administrative_unit_level_code, state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

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
