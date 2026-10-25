# villages

LGD's village register includes English/local names, version,
state/district/subdistrict references, census identifiers and, where
supplied, status, category and remarks. A row represents a
`village_code`/`village_category` pair: the same village can have several
reported categories. Count distinct village codes when counting places.

The parent codes connect to the administrative registers. Block and
local-body associations are supplied separately by reports such as
[villages_by_blocks](villages_by_blocks.md) and [gp_mapping](gp_mapping.md).
Status and category retain the source's claims; they are not inferred
from membership in a mapping report.

## Row identity and conversion

The known header typo `Village Name (In Englsih)` is accepted.

The reported record key is:

```text
(village_code, village_category)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_version` | `INTEGER` | `Village Version` | No |
| 3 | `village_name` | `VARCHAR` | `Village Name (In English)` | No |
| 4 | `village_name_local` | `VARCHAR` | `Village Name (In Local)` | Yes → NULL |
| 5 | `village_status` | `VARCHAR` | `Village Status` | Yes → NULL |
| 6 | `village_category` | `VARCHAR` | `Village Category` | Yes → NULL |
| 7 | `remark` | `VARCHAR` | `Remark` | Yes → NULL |
| 8 | `state_code` | `VARCHAR` | `State Code` | No |
| 9 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 10 | `district_code` | `VARCHAR` | `District Code` | No |
| 11 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 12 | `subdistrict_code` | `VARCHAR` | `Sub-District Code` | No |
| 13 | `subdistrict_name` | `VARCHAR` | `Sub-District Name (In English)` | No |
| 14 | `village_census_2001_code` | `VARCHAR` | `Census 2001 Code` | No |
| 15 | `village_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
