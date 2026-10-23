# pincode_villages

One reported village/pincode/administrative-path association. A village may have several pincodes. Pincodes and census codes remain strings; the converter does not enforce a fabricated one-to-one postal relationship.

## Row identity and conversion

The reported record key is:

```text
(village_code, pincode, state_code, district_code, subdistrict_code)
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
| 3 | `pincode` | `VARCHAR` | `Pincode` | No |
| 4 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 5 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name` | No |
| 6 | `district_code` | `VARCHAR` | `District Code` | No |
| 7 | `district_name` | `VARCHAR` | `District Name` | No |
| 8 | `state_code` | `VARCHAR` | `State Code` | No |
| 9 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
