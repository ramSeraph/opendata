# pri_local_body_wards

One reported ward/body/state/name-path variant. Repeated ward codes with differing reported body or parent names remain separate rows. Use COUNT(DISTINCT ward_code) to count ward codes. This preservation decision may be revisited; no variant is currently selected as authoritative. Known Word Code, Word Number and Disrtict Level Parent Name header typos are accepted.

## Row identity and conversion

The reported record key is:

```text
(ward_code, local_body_code, state_code, local_body_name, district_panchayat_name, intermediate_panchayat_name)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `ward_code` | `VARCHAR` | `Ward Code` | No |
| 2 | `ward_number` | `VARCHAR` | `Ward Number` | No |
| 3 | `ward_name` | `VARCHAR` | `Ward Name (In English)` | No |
| 4 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 5 | `local_body_name` | `VARCHAR` | `Local Body Name` | No |
| 6 | `state_code` | `VARCHAR` | `State Code` | No |
| 7 | `state_name` | `VARCHAR` | `State Name` | No |
| 8 | `ward_name_local` | `VARCHAR` | `Ward Name (In Local)` | No |
| 9 | `local_body_type_name` | `VARCHAR` | `Local Body Type` | No |
| 10 | `district_panchayat_name` | `VARCHAR` | `District Level Parent Name` | No |
| 11 | `intermediate_panchayat_name` | `VARCHAR` | `Intermediate Level Parent Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
