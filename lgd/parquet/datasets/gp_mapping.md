# gp_mapping

One reported village/local-body/administrative-path association. A village may map to multiple local bodies. Blank village/subdistrict codes are accepted only with consistent empty dependent fields. A whitespace-only local-body code is retained only when its corresponding name is empty. Census-header word-order variants are accepted.

## Row identity and conversion

The reported record key is:

```text
(village_code, local_body_code, state_code, district_code, subdistrict_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name (in English)` | No |
| 3 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 4 | `local_body_name` | `VARCHAR` | `Local Body Name (in English)` | No |
| 5 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 6 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name (in English)` | No |
| 7 | `district_code` | `VARCHAR` | `District Code` | No |
| 8 | `district_name` | `VARCHAR` | `District Name (in English)` | No |
| 9 | `state_code` | `VARCHAR` | `State Code` | No |
| 10 | `state_name` | `VARCHAR` | `State Name` | No |
| 11 | `village_census_2011_code` | `VARCHAR` | `Village Census 2011 Code` | No |
| 12 | `village_census_2001_code` | `VARCHAR` | `Village Census 2001 Code` | No |
| 13 | `subdistrict_census_2011_code` | `VARCHAR` | `Subdistrict Census Code 2011` | No |
| 14 | `subdistrict_census_2001_code` | `VARCHAR` | `Subdistrict Census Code 2001` | No |
| 15 | `district_census_2011_code` | `VARCHAR` | `District Census 2011 Code` | No |
| 16 | `district_census_2001_code` | `VARCHAR` | `District Census 2001 Code` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
