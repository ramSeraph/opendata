# changes

The discontinued LGD change report records entity type/code,
version, names, census reference, operation and reported date. It
supplies structured entity references and retains every source row,
including duplicate or repeated claims; the report serial is not a
stable event identifier.

This is one cumulative event table, not a sequence of entity snapshots.
Its row-date range does not prove complete collection coverage. The
newer [transactions](transactions.md) report has a different schema
and cannot be treated as the same event stream under renamed fields.

## Row identity and conversion

`report_serial` remains text and may contain thousands separators.
`report_date` is parsed losslessly from `DD-MM-YYYY`; `entity_version`
must be a nonnegative integer. `census_code` preserves source sentinels
such as the literal string `null`.

No uniqueness key is imposed and no source rows are deduplicated. This is one
cumulative event report, with no observation or interval columns.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `report_serial` | `VARCHAR` | `S.No.` | No |
| 2 | `entity_type` | `VARCHAR` | `Entity Type` | No |
| 3 | `entity_code` | `VARCHAR` | `Entity Code` | No |
| 4 | `entity_version` | `INTEGER` | `Entity Version` | No |
| 5 | `entity_name` | `VARCHAR` | `Entity Name (In English)` | No |
| 6 | `entity_name_local` | `VARCHAR` | `Entity Name (In Local)` | No |
| 7 | `census_code` | `VARCHAR` | `Census Code` | No |
| 8 | `operation_name` | `VARCHAR` | `Operation` | No |
| 9 | `report_date` | `DATE` | `date` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
