# pri_local_bodies

One reported Panchayati Raj local body. A top-level body can legitimately have a blank `parent_local_body_code`. Parent references and names are supplied values, not independently resolved foreign keys.

## Row identity and conversion

The reported record key is:

```text
(local_body_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Localbody Code` | No |
| 2 | `local_body_version` | `INTEGER` | `Localbody Version` | No |
| 3 | `local_body_name` | `VARCHAR` | `Localbody Name (In English)` | No |
| 4 | `local_body_name_local` | `VARCHAR` | `Localbody Name (In Local)` | No |
| 5 | `local_body_type_code` | `VARCHAR` | `Localbody Type Code` | No |
| 6 | `local_body_type_name` | `VARCHAR` | `Localbody Type Name` | No |
| 7 | `parent_local_body_code` | `VARCHAR` | `Parent Localbody Code` | No |
| 8 | `state_code` | `VARCHAR` | `State Code` | No |
| 9 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
