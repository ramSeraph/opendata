# villages_by_blocks

One reported village/block/local-body/administrative-path association. Block district fields are separate from the village district fields. Optional field groups must appear together: block district code/name; local-body code/name/census code. Only the exact repeated split-header signature is removed, with a count in the conversion receipt. Source typos such as `VillageCunsecCode` have explicit aliases.

## Row identity and conversion

The reported record key is:

```text
(village_code, block_code, local_body_code, state_code, district_code, subdistrict_code, block_district_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name (In English)` | No |
| 3 | `block_code` | `VARCHAR` | `Development Block Code` | No |
| 4 | `block_name` | `VARCHAR` | `Development Block Name (In English)` | No |
| 5 | `local_body_code` | `VARCHAR` | `Local Body Code` | Yes → NULL |
| 6 | `local_body_name` | `VARCHAR` | `Local Body Name (In English)` | Yes → NULL |
| 7 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 8 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name (In English)` | No |
| 9 | `district_code` | `VARCHAR` | `District Code` | No |
| 10 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 11 | `state_code` | `VARCHAR` | `State Code` | No |
| 12 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 13 | `village_census_2011_code` | `VARCHAR` | `Village Census 2011 Code` | No |
| 14 | `subdistrict_census_2011_code` | `VARCHAR` | `Subdistrict Census 2011 Code` | No |
| 15 | `district_census_2011_code` | `VARCHAR` | `District Census 2011 Code` | No |
| 16 | `state_census_2011_code` | `VARCHAR` | `State Census 2011 Code` | No |
| 17 | `local_body_census_2011_code` | `VARCHAR` | `Local Body 2011 Code` | Yes → NULL |
| 18 | `block_district_code` | `VARCHAR` | `District Code of Development Block` | Yes → NULL |
| 19 | `block_district_name` | `VARCHAR` | `District Name of Development Block (In English)` | Yes → NULL |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
