# invalidated_census_villages

One reported invalidated village/state record. A blank village code can represent a state-only placeholder, but all village and census attributes must then be empty. Census columns are optional. State LGD Code/Village LGD Code and the corresponding English-name aliases are accepted. Source rows do not independently establish when a village was invalidated.

## Row identity and conversion

The reported record key is:

```text
(village_code, state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name(In English)` | No |
| 3 | `state_code` | `VARCHAR` | `State Code` | No |
| 4 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 5 | `village_census_2001_code` | `VARCHAR` | `Census Code 2001` | Yes → NULL |
| 6 | `village_census_2011_code` | `VARCHAR` | `Census Code 2011` | Yes → NULL |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
