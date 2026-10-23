# constituencies_mapping_pri

One reported village/body/block/administrative-path/constituency association. The local-body name is part of the record identity because the source reports alternative named associations. ECI codes remain separate from LGD codes. Blank body, block, assembly and ECI references are retained as reported.

## Row identity and conversion

The reported record key is:

```text
(village_code, local_body_code, local_body_name, block_code, state_code, district_code, subdistrict_code, parliament_constituency_code, assembly_constituency_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name` | No |
| 3 | `village_census_2011_code` | `VARCHAR` | `Village Census 2011 Code` | No |
| 4 | `local_body_code` | `VARCHAR` | `Rural Localbody Code` | No |
| 5 | `local_body_name` | `VARCHAR` | `Rural LocalbodyName` | No |
| 6 | `block_code` | `VARCHAR` | `Block Code` | No |
| 7 | `block_name` | `VARCHAR` | `Block Name` | No |
| 8 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 9 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name` | No |
| 10 | `subdistrict_census_2011_code` | `VARCHAR` | `Subdistrict Census 2011 Code` | No |
| 11 | `district_code` | `VARCHAR` | `District Code` | No |
| 12 | `district_name` | `VARCHAR` | `District Name` | No |
| 13 | `district_census_2011_code` | `VARCHAR` | `District Census 2011 Code` | No |
| 14 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency code` | No |
| 15 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 16 | `parliament_constituency_eci_code` | `VARCHAR` | `Parliament Constituency ECI Code` | No |
| 17 | `assembly_constituency_code` | `VARCHAR` | `Assembly Constituency Code` | No |
| 18 | `assembly_constituency_name` | `VARCHAR` | `Assembly Constituency Name` | No |
| 19 | `assembly_constituency_eci_code` | `VARCHAR` | `Assembly Constituency ECI Code` | No |
| 20 | `state_code` | `VARCHAR` | `State Code` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
