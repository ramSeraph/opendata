# state_orgs

One reported organization/state pair. A parent organization may appear only as a reference, so no parent row is synthesized. Type labels and blank parent codes are retained as supplied.

## Row identity and conversion

The reported record key is:

```text
(organization_code, state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `organization_code` | `VARCHAR` | `Organization Code` | No |
| 2 | `organization_name` | `VARCHAR` | `Organization Name` | No |
| 3 | `organization_type` | `VARCHAR` | `Organization Type` | No |
| 4 | `parent_organization_code` | `VARCHAR` | `Parent Organization Code` | No |
| 5 | `parent_organization_name` | `VARCHAR` | `Parent Organization Name` | No |
| 6 | `parent_organization_type` | `VARCHAR` | `Parent Organization Type` | No |
| 7 | `state_code` | `VARCHAR` | `State Code` | No |
| 8 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
