# central_orgs

One reported central organization. This report has no state columns. Parent ministries may appear only as references; no additional rows or state identifiers are synthesized. Type labels and blank parent codes remain source values.

## Row identity and conversion

The reported record key is:

```text
(organization_code)
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

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
