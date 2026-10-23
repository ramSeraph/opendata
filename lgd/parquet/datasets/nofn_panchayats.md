# nofn_panchayats

One reported panchayat/state/named-district/named-subdistrict association. The report supplies parent names without district or subdistrict codes. Preserve each named association; do not manufacture codes or presume that the retired source describes current network availability. SR.NO is accepted as the discarded row serial.

## Row identity and conversion

The reported record key is:

```text
(local_body_code, state_code, district_name, subdistrict_name)
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
| 3 | `district_name` | `VARCHAR` | `District Name` | No |
| 4 | `subdistrict_name` | `VARCHAR` | `Sub District Name(In English)` | No |
| 5 | `state_code` | `VARCHAR` | `State Code` | No |
| 6 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
