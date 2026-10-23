# pincode_urban

One reported urban-local-body/state/pincode association. A body may have multiple pincodes. Pincodes remain strings, and names remain the labels supplied by this report.

## Row identity and conversion

The reported record key is:

```text
(local_body_code, state_code, pincode)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

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
