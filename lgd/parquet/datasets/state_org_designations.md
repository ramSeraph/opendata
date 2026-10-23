# state_org_designations

One reported designation/organization/location-level association. Level names are part of the identity because a level code can have several reported names. A designation can belong to several levels. Local-language names remain text. State codes are part of the identity.

## Row identity and conversion

The reported record key is:

```text
(designation_code, organization_code, organization_level_code, organization_level_name, state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `designation_code` | `VARCHAR` | `Designation Code` | No |
| 2 | `designation_name` | `VARCHAR` | `Designation Name (In English)` | No |
| 3 | `designation_name_local` | `VARCHAR` | `Designation Name Local (In Local)` | No |
| 4 | `organization_level_code` | `VARCHAR` | `Org Located Level Code` | No |
| 5 | `organization_level_name` | `VARCHAR` | `Org Level Specific Name` | No |
| 6 | `organization_code` | `VARCHAR` | `Base Organization Code` | No |
| 7 | `organization_name` | `VARCHAR` | `Base Organization Name` | No |
| 8 | `state_code` | `VARCHAR` | `State Code` | No |
| 9 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
