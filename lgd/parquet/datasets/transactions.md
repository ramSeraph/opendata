# transactions

LGD's newer cumulative event report supplies transaction ID,
operation code/name, date, state scope and a description. Descriptions
are free text that can mention several entities; the report does not
provide those mentions as structured entity relationships. State
scope `0` can describe the Centre.

Every reported row is retained, including repeated IDs and differing
descriptions. This is one event table without snapshot validity
intervals. Collection coverage is tracked separately from event dates,
and the earlier [changes](changes.md) report remains a separate dataset.

## Row identity and conversion

`transaction_date` is parsed losslessly from `DD-Mon-YYYY`.

No uniqueness key is imposed and no source rows are deduplicated. This is one
cumulative event report, with no observation or interval columns.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `transaction_id` | `VARCHAR` | `Transaction ID` | No |
| 2 | `operation_code` | `VARCHAR` | `Operation Code` | No |
| 3 | `operation_name` | `VARCHAR` | `Operation Name` | No |
| 4 | `description` | `VARCHAR` | `Description` | No |
| 5 | `transaction_date` | `DATE` | `Transaction Date` | No |
| 6 | `state_code` | `VARCHAR` | `State Code` | No |
| 7 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
