# states

One reported state or union territory. `state_or_ut` is the supplied classification. Census identifiers and the LGD state code are separate namespaces; local names are optional.

## Row identity and conversion

The reported record key is:

```text
(state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `state_code` | `VARCHAR` | `State Code` | No |
| 2 | `state_version` | `INTEGER` | `State Version` | No |
| 3 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 4 | `state_name_local` | `VARCHAR` | `State Name (In Local)` | Yes → NULL |
| 5 | `state_census_2001_code` | `VARCHAR` | `Census 2001 Code` | No |
| 6 | `state_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |
| 7 | `state_or_ut` | `VARCHAR` | `State or UT` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
