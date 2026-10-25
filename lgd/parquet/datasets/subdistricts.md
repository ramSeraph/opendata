# subdistricts

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/subdistricts.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

LGD's subdistrict register, with English names, versions, district and
state references, and 2001/2011 census identifiers. Each row identifies
one subdistrict by `subdistrict_code`; its version and administrative
parents are attributes.

Parent codes connect to [districts](districts.md) and [states](states.md),
while their supplied names support lookups without those joins. A
subdistrict and a development block have separate LGD identifiers;
[blocks](blocks.md) describes the latter.

## Row identity and conversion

The reported record key is:

```text
(subdistrict_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `subdistrict_code` | `VARCHAR` | `Sub-district Code` | No |
| 2 | `subdistrict_version` | `INTEGER` | `Sub-district Version` | No |
| 3 | `subdistrict_name` | `VARCHAR` | `Sub-district Name` | No |
| 4 | `district_code` | `VARCHAR` | `District Code` | No |
| 5 | `district_name` | `VARCHAR` | `District Name` | No |
| 6 | `state_code` | `VARCHAR` | `State Code` | No |
| 7 | `state_name` | `VARCHAR` | `State Name` | No |
| 8 | `subdistrict_census_2001_code` | `VARCHAR` | `Census 2001 Code` | No |
| 9 | `subdistrict_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |
