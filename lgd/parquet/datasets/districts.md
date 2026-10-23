# districts

One reported district with its supplied state reference. Parent names remain verbatim even when another report spells the same parent differently. Census identifiers are distinct from the LGD district code.

## Row identity and conversion

The reported record key is:

```text
(district_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `district_code` | `VARCHAR` | `District Code` | No |
| 2 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 3 | `state_code` | `VARCHAR` | `State Code` | No |
| 4 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 5 | `district_census_2001_code` | `VARCHAR` | `Census 2001 Code` | No |
| 6 | `district_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
