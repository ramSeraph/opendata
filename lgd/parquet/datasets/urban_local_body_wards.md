# urban_local_body_wards

One reported urban ward. Ward numbers are text, not counts or identifiers interchangeable with ward_code. The body census code is optional; both Census Code 2011 and the canonical source header are accepted.

## Row identity and conversion

The reported record key is:

```text
(ward_code)
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
| 3 | `ward_name` | `VARCHAR` | `Ward Name` | No |
| 4 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 5 | `local_body_name` | `VARCHAR` | `Local Body Name` | No |
| 6 | `state_code` | `VARCHAR` | `State Code` | No |
| 7 | `state_name` | `VARCHAR` | `State Name` | No |
| 8 | `local_body_census_2011_code` | `VARCHAR` | `Census 2011 Code` | Yes → NULL |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
