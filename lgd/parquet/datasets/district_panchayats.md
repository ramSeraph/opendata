# district_panchayats

This report connects district panchayats to administrative districts,
supplying both codes/names and the state. A panchayat can be linked to
several districts, and a district can be linked to several panchayats.
The association is identified by
`(district_panchayat_code, district_code)`; state is an attribute.

Resolve the panchayat code as a local-body code in
[pri_local_bodies](pri_local_bodies.md), and the district code in
[districts](districts.md). The two identifiers describe different
institutions and need not form a one-to-one hierarchy.

## Row identity and conversion

The source typo `Disrict Code` is accepted as `district_code`.

The reported record key is:

```text
(district_panchayat_code, district_code)
```

`state_code` is a reported attribute used for filtering and coverage checks;
it is not part of the association's identity. Identical records collapse.
Conflicting attributes for this key, including different state codes within
the same report, are rejected;
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
