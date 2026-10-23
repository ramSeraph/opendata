# constituencies_mapping_urban

One reported ward/body/administrative-path/parliamentary-and-assembly association. ECI constituency codes are a separate namespace from LGD constituency codes. Blank assembly and ECI codes, and blank district/subdistrict references, are retained as reported. This report is not proof of complete constituency coverage.

## Row identity and conversion

The reported record key is:

```text
(ward_code, local_body_code, state_code, district_code, subdistrict_code, parliament_constituency_code, assembly_constituency_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `ward_code` | `VARCHAR` | `Ward Code` | No |
| 2 | `ward_name` | `VARCHAR` | `Ward Name` | No |
| 3 | `local_body_code` | `VARCHAR` | `Urban Localbody Code` | No |
| 4 | `local_body_name` | `VARCHAR` | `Urban Localbody Name` | No |
| 5 | `local_body_type_name` | `VARCHAR` | `Localbody Type` | No |
| 6 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency code` | No |
| 7 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 8 | `parliament_constituency_eci_code` | `VARCHAR` | `Parliament Constituency ECI Code` | No |
| 9 | `assembly_constituency_code` | `VARCHAR` | `Assembly Constituency Code` | No |
| 10 | `assembly_constituency_name` | `VARCHAR` | `Assembly Constituency Name` | No |
| 11 | `assembly_constituency_eci_code` | `VARCHAR` | `Assembly Constituency ECI Code` | No |
| 12 | `district_code` | `VARCHAR` | `District Code` | No |
| 13 | `district_name` | `VARCHAR` | `District Name` | No |
| 14 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 15 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name` | No |
| 16 | `state_code` | `VARCHAR` | `State Code` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
