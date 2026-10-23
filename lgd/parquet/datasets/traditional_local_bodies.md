# traditional_local_bodies

One reported local-body/parent-path association. `local_body_level` (District, Intermediate or Village) and `local_body_type_name` describe different concepts. Older layouts can supply a type while newer ones supply a level; at least one of type code or level must be present. An absent type field becomes NULL. Blank parent codes are permitted.

## Row identity and conversion

The reported record key is:

```text
(local_body_code, district_panchayat_code, intermediate_panchayat_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Localbody Code` | No |
| 2 | `local_body_version` | `INTEGER` | `Localbody Version` | Yes → NULL |
| 3 | `local_body_name` | `VARCHAR` | `Localbody Name (In English)` | No |
| 4 | `local_body_name_local` | `VARCHAR` | `Localbody Name (In Local)` | Yes → NULL |
| 5 | `local_body_type_code` | `VARCHAR` | `Localbody Type Code` | Yes → NULL |
| 6 | `local_body_type_name` | `VARCHAR` | `Localbody Type Name` | Yes → NULL |
| 7 | `district_panchayat_code` | `VARCHAR` | `District Panchayat Code` | No |
| 8 | `intermediate_panchayat_code` | `VARCHAR` | `Intermediate/Block Panchayat Code` | No |
| 9 | `state_code` | `VARCHAR` | `State Code` | No |
| 10 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 11 | `local_body_level` | `VARCHAR` | `Local Body Level` | Yes → NULL |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
