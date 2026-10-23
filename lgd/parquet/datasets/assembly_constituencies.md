# assembly_constituencies

One reported assembly/parliamentary-constituency/state association. A blank assembly code is a retained placeholder only if its assembly name is also blank. Serial numbers must be contiguous and begin at 1 or the recognized defective prefix 81. A precise timestamp-only footer may be ignored. Missing prefix rows are reported in the receipt and are not fabricated.

## Row identity and conversion

The reported record key is:

```text
(assembly_constituency_code, parliament_constituency_code, state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `assembly_constituency_code` | `VARCHAR` | `Assembly Constituency Code` | No |
| 2 | `assembly_constituency_name` | `VARCHAR` | `Assembly Constituency Name` | No |
| 3 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency Code` | No |
| 4 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 5 | `state_code` | `VARCHAR` | `State Code` | No |
| 6 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
