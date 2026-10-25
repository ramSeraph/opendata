# states

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/states.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

LGD's register of states and union territories, with English and local
names, the reported state/UT classification, version and 2001/2011 census
identifiers. Each row identifies one state or union territory by
`state_code`.

Use this register to resolve state references in other datasets.
`state_or_ut` retains LGD's classification, and census identifiers remain
separate from LGD codes. Optional local names may be absent.

## Row identity and conversion

The reported record key is:

```text
(state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `state_code` | `VARCHAR` | `State Code` | No |
| 2 | `state_version` | `INTEGER` | `State Version` | No |
| 3 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 4 | `state_name_local` | `VARCHAR` | `State Name (In Local)` | Yes → NULL |
| 5 | `state_census_2001_code` | `VARCHAR` | `Census 2001 Code` | No |
| 6 | `state_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |
| 7 | `state_or_ut` | `VARCHAR` | `State or UT` | No |
