# transactions

Every reported transaction row is retained, including repeated state/transaction IDs or differing descriptions. transaction_date is parsed losslessly from DD-Mon-YYYY. State code 0 can describe Center. description is free text that may mention several entities; it is not a structured relationship list. Row dates do not establish complete collection coverage, which is recorded separately by the source collector.

## Row identity and conversion

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
