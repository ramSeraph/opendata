# parliament_constituencies_lb_mapping

This legacy report links parliamentary constituencies to named
assembly constituencies and local bodies, with a body-type name,
state and coverage flag. The parliamentary reference is coded; assembly
and local-body references are names. Those names identify reported
associations here and cannot safely be converted to unique LGD codes
from spelling alone.

State and full/partial coverage are attributes. Simultaneous `F`/`P`
claims become one association with NULL coverage, with both originals
recoverable; literal blank coverage remains blank. The retained
source ends in December 2022, so its links describe a historical report.

## Row identity and conversion

The reported record key is:

```text
(parliament_constituency_code, assembly_constituency_name, local_body_name, local_body_type_name)
```

Identical records collapse. When the source supplies both `F` and `P` for this
association, one row has `coverage_type=NULL`: unresolved conflicting claims.
The converter's checksum-pinned discrepancy Parquet retains both original rows,
and `conflicting_coverage_rows` counts normalized associations with conflicts.
Literal blank coverage remains `''`, distinct from NULL. Unknown flags or a
blank co-reported with a supplied flag stop conversion for review. Other
attribute conflicts, including state or parliamentary-name disagreement, also
stop conversion; no name/code lookup or coverage adjudication is performed.

The historical review
finds that state is redundant throughout the retained history and that all
simultaneous coverage conflicts are exactly `F`/`P` pairs.

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
