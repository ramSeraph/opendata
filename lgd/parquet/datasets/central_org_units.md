# central_org_units

One reported organization-unit/organization association. Parent-unit and location-level references are reported labels and codes, not verified foreign keys. Entity codes can be signed source sentinels; blank parent and level codes remain blank. This central report has no state columns.

## Row identity and conversion

The reported record key is:

```text
(organization_unit_code, organization_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `organization_unit_code` | `VARCHAR` | `Org Unit Code` | No |
| 2 | `organization_unit_name` | `VARCHAR` | `Org Unit Name (In English)` | No |
| 3 | `organization_unit_name_local` | `VARCHAR` | `Org Unit Name (In Local)` | No |
| 4 | `entity_type` | `VARCHAR` | `Entity Type` | No |
| 5 | `entity_code` | `VARCHAR` | `Entity Lc` | No |
| 6 | `parent_organization_unit_code` | `VARCHAR` | `Parent Org Unit Code` | No |
| 7 | `parent_organization_unit_name` | `VARCHAR` | `Parent Org Unit Name` | No |
| 8 | `organization_level_code` | `VARCHAR` | `Org Located Level Code` | No |
| 9 | `organization_code` | `VARCHAR` | `Base Organization Code` | No |
| 10 | `organization_name` | `VARCHAR` | `Base Organization Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
