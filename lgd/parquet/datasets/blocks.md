# blocks

One reported block/district association. A block may be reported against more than one district, so count distinct `block_code` for entity counts. Both Block and Development Block header spellings are accepted.

## Row identity and conversion

The reported record key is:

```text
(block_code, district_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `block_code` | `VARCHAR` | `Block Code` | No |
| 2 | `block_version` | `INTEGER` | `Block Version` | No |
| 3 | `block_name` | `VARCHAR` | `Block Name (In English)` | No |
| 4 | `block_name_local` | `VARCHAR` | `Block Name (In Local)` | No |
| 5 | `district_code` | `VARCHAR` | `District Code` | No |
| 6 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 7 | `state_code` | `VARCHAR` | `State Code` | No |
| 8 | `state_name` | `VARCHAR` | `State Name (In English)` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
