# statewise_ulbs_coverage

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/statewise_ulbs_coverage.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This report links urban local bodies to reported district,
subdistrict and village coverage. It includes both complete village
paths and district/subdistrict-only rows. The association key retains
`(local_body_code, district_code, subdistrict_code, village_code)`;
body/village alone cannot distinguish paths with missing lower levels.

A body can have several geographic associations. Blank or zero child
references do not identify a village. The report supplies state names
without state codes; conversion does not invent those codes or infer
ward locations from body-level coverage.

## Row identity and conversion

Blank or zero lower-level codes are retained only when dependent names
and children are consistently empty.

The reported record key is:

```text
(local_body_code, district_code, subdistrict_code, village_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 2 | `local_body_name` | `VARCHAR` | `Local Body Name (In English)` | No |
| 3 | `district_code` | `VARCHAR` | `District Code` | No |
| 4 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 5 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 6 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name (In English)` | No |
| 7 | `village_code` | `VARCHAR` | `Village Code` | No |
| 8 | `village_name` | `VARCHAR` | `Village Name (In English)` | No |
| 9 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 10 | `local_body_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |
