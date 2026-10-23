# district_panchayats

One reported district-panchayat/district/state association. A panchayat code can occur against several districts. The source typo `Disrict Code` is accepted as district_code.

## Row identity and conversion

The reported record key is:

```text
(district_panchayat_code, district_code, state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `district_panchayat_code` | `VARCHAR` | `District Panchayat Code` | No |
| 2 | `district_panchayat_name` | `VARCHAR` | `District Panchayat` | No |
| 3 | `district_code` | `VARCHAR` | `District Code` | No |
| 4 | `district_name` | `VARCHAR` | `District Name` | No |
| 5 | `state_code` | `VARCHAR` | `State Code` | No |
| 6 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
