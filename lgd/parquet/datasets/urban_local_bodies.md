# urban_local_bodies

One reported urban local body. LGD and census local-body codes remain distinct. `local_body_type_code` and its name describe the reported body type, not a hierarchy level. Both State Name header spellings are accepted.

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
| 1 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 2 | `local_body_version` | `INTEGER` | `Local Body Version` | No |
| 3 | `local_body_name` | `VARCHAR` | `Local Body Name (In English)` | No |
| 4 | `local_body_name_local` | `VARCHAR` | `Local Body Name (In Local)` | No |
| 5 | `local_body_type_code` | `VARCHAR` | `Localbody Type Code` | No |
| 6 | `local_body_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |
| 7 | `state_code` | `VARCHAR` | `State Code` | No |
| 8 | `state_name` | `VARCHAR` | `State Name (In English)` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
