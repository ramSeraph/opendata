# parliament_constituencies_lb_mapping

One reported parliamentary-constituency/state/named-local-body coverage claim. Assembly and local-body references in this report are names, not structured codes. The source body type and coverage description remain strings. Do not infer a unique local-body code from a name alone.

## Row identity and conversion

The reported record key is:

```text
(parliament_constituency_code, state_code, assembly_constituency_name, local_body_name, local_body_type_name, coverage_type)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency Code` | No |
| 2 | `parliament_constituency_name` | `VARCHAR` | `Parliament` | No |
| 3 | `assembly_constituency_name` | `VARCHAR` | `Assembly` | No |
| 4 | `local_body_name` | `VARCHAR` | `Local Gov. Name` | No |
| 5 | `local_body_type_name` | `VARCHAR` | `Classification` | No |
| 6 | `coverage_type` | `VARCHAR` | `Coverage` | No |
| 7 | `state_code` | `VARCHAR` | `State Code` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
