# tlb_villages

One reported village/block/traditional-body/administrative-path association. Local-body type code/name are optional but must be supplied together. When both state-name columns are present their values must agree exactly. Blank village, subdistrict, block and body references require consistent empty names and dependent fields.

## Row identity and conversion

The reported record key is:

```text
(village_code, block_code, local_body_code, state_code, district_code, subdistrict_code)
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
| 3 | `local_body_code` | `VARCHAR` | `Gram Panchayat/ TLB Code` | No |
| 4 | `local_body_name` | `VARCHAR` | `Gram Panchayat/ TLB (In English)` | No |
| 5 | `local_body_type_code` | `VARCHAR` | `Gram Panchayat/ TLB Type Code` | Yes → NULL |
| 6 | `local_body_type_name` | `VARCHAR` | `Gram Panchayat/ TLB Type Name` | Yes → NULL |
| 7 | `block_code` | `VARCHAR` | `Block Code` | No |
| 8 | `block_name` | `VARCHAR` | `Block Name (In English)` | No |
| 9 | `subdistrict_code` | `VARCHAR` | `Sub-district Code` | No |
| 10 | `subdistrict_name` | `VARCHAR` | `Sub-district Name (In English)` | No |
| 11 | `district_code` | `VARCHAR` | `District Code` | No |
| 12 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 13 | `state_code` | `VARCHAR` | `State Code` | No |
| 14 | `state_name` | `VARCHAR` | `State Name` | No |
| 15 | `state_census_2011_code` | `VARCHAR` | `State Census 2011 Code` | No |
| 16 | `district_census_2011_code` | `VARCHAR` | `District Census 2011 Code` | No |
| 17 | `subdistrict_census_2011_code` | `VARCHAR` | `Sub-district Census 2011 code` | No |
| 18 | `village_census_2011_code` | `VARCHAR` | `Village Census 2011 Code` | No |
| 19 | `local_body_census_2011_code` | `VARCHAR` | `Gram Panchayat/ TLB Census 2011 Code` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
