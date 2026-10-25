# villages_by_blocks

This report associates villages with development blocks and, where
supplied, local bodies. It includes village administrative paths and
census references. Distinct block/body associations remain separate:
even the same village and local body can be reported under several
blocks. Row counts therefore need not count distinct villages.

`district_code` and `district_name` describe the village. The source's conflicting
block-district columns are omitted from normalized output; consult
[blocks](blocks.md) for reported block/district associations. Removing
those columns collapses duplicate assertions without discarding a
distinct village/block/local-body link.

## Row identity and conversion

The reported record key is:

```text
(village_code, block_code, local_body_code, state_code, district_code, subdistrict_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

State and village-district codes remain part of the historical path key: older
reports contain simultaneous administrative paths and blank-village placeholders.
Removing block-district fields does not resolve those separate source issues.

The local-body code/name/census columns are optional but must appear together.
The retired block-district headers must also appear as a pair when supplied.
Source headers, supplied-field schema IDs and the conversion receipt's
`omitted_source_fields` preserve the layout evidence. IDs **18 and 19 are retired**
and must not be reused. Exact repeated split-header rows are counted separately;
source aliases such as `VillageCunsecCode` remain supported.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name (In English)` | No |
| 3 | `block_code` | `VARCHAR` | `Development Block Code` | No |
| 4 | `block_name` | `VARCHAR` | `Development Block Name (In English)` | No |
| 5 | `local_body_code` | `VARCHAR` | `Local Body Code` | Yes → NULL |
| 6 | `local_body_name` | `VARCHAR` | `Local Body Name (In English)` | Yes → NULL |
| 7 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 8 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name (In English)` | No |
| 9 | `district_code` | `VARCHAR` | `District Code` | No |
| 10 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 11 | `state_code` | `VARCHAR` | `State Code` | No |
| 12 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 13 | `village_census_2011_code` | `VARCHAR` | `Village Census 2011 Code` | No |
| 14 | `subdistrict_census_2011_code` | `VARCHAR` | `Subdistrict Census 2011 Code` | No |
| 15 | `district_census_2011_code` | `VARCHAR` | `District Census 2011 Code` | No |
| 16 | `state_census_2011_code` | `VARCHAR` | `State Census 2011 Code` | No |
| 17 | `local_body_census_2011_code` | `VARCHAR` | `Local Body 2011 Code` | Yes → NULL |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
