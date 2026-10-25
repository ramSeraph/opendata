# pincode_urban

LGD's urban-body/pincode report supplies local-body and postal-code
associations with body and state names/codes. A body may have several
pincodes. The record key is `(local_body_code, pincode)`; state code/name
remain attributes and filters.

Body codes usually connect to [urban_local_bodies](urban_local_bodies.md).
Historical reports also contain rural/traditional bodies, which can require
the [PRI](pri_local_bodies.md) or [traditional-body](traditional_local_bodies.md)
registers; the dataset name does not restrict its contents to urban bodies.
Pincodes remain text and identify postal references rather than LGD
entities. These links do not supply ward-level addresses or postal
delivery boundaries.

## Row identity and conversion

The reported record key is:

```text
(local_body_code, pincode)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

Across 1,415 retained observations from 12 September 2022 through 19 October
2026, all 7,895 historical body/pincode pairs have no simultaneous conflicting
rows under this key. Each of the 5,248 body codes belongs to one reported state.
State is not needed to distinguish links.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Localbody Code` | No |
| 2 | `local_body_name` | `VARCHAR` | `Localbody Name` | No |
| 3 | `local_body_type_name` | `VARCHAR` | `Localbody Type Name` | No |
| 4 | `pincode` | `VARCHAR` | `Pincode` | No |
| 5 | `state_code` | `VARCHAR` | `State Code` | No |
| 6 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
