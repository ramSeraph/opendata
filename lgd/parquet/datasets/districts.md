# districts

LGD's district register: one district per `district_code`, with its
English name, state code/name and 2001/2011 census identifiers. State is
a reported parent attribute, so a changed state reference updates the
district rather than creating a different district identity.

State names are already supplied for ordinary lookups. Use `state_code`
to connect to [states](states.md); labels may differ between reports.
District census codes belong to a different namespace from LGD codes.

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
