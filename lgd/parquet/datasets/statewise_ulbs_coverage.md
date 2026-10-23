# statewise_ulbs_coverage

One reported urban-body/district/subdistrict/village association. This report supplies state names rather than state codes; the converter does not invent a state code. Blank or zero lower-level codes are retained only when dependent names and children are consistently empty.

## Row identity and conversion

The reported record key is:

```text
(local_body_code, district_code, subdistrict_code, village_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 2 | `local_body_name` | `VARCHAR` | `Local Body Name (In English)` | No |
| 3 | `district_code` | `VARCHAR` | `District Code` | No |
| 4 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 5 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 6 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name (In English)` | No |
| 7 | `village_code` | `VARCHAR` | `Village Code` | No |
| 8 | `village_name` | `VARCHAR` | `Village Name (In English)` | No |
| 9 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 10 | `local_body_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
