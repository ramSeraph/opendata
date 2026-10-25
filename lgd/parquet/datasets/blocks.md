# blocks

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/blocks.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

LGD's development-block register contains block codes, names,
versions and reported district/state references. Each row represents
a block/district association. A block can appear against several
districts, so row counts and distinct `block_code` counts differ.

Use this report for the block's district associations and
[villages_by_blocks](villages_by_blocks.md) for its reported village
links. Block codes, subdistrict codes and panchayat codes identify
different entities, even where their names or numbers resemble one another.

## Row identity and conversion

Both Block and Development Block header spellings are accepted.

The reported record key is:

```text
(block_code, district_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

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
