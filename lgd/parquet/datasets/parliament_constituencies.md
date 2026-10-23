# parliament_constituencies

One reported parliamentary constituency/state pair. Some source layouts include empty assembly columns; these are dropped only after verifying that all values are blank. Serial numbers must be contiguous and begin at 1 or the recognized defective prefix 81. A precise timestamp-only footer may be ignored. Missing prefix rows are reported in the receipt and are not fabricated.

## Row identity and conversion

The reported record key is:

```text
(parliament_constituency_code, state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency Code` | No |
| 2 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 3 | `state_code` | `VARCHAR` | `State Code` | No |
| 4 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
