# urban_local_bodies

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/urban_local_bodies.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

LGD's urban local-body register supplies a body's LGD code, names,
version, type, state and census identifier. Each row identifies one
body by `local_body_code`. The type code/name classifies the body;
it does not describe a tier in the PRI hierarchy.

Use [urban_local_body_wards](urban_local_body_wards.md) for its wards
and [statewise_ulbs_coverage](statewise_ulbs_coverage.md) for reported
district/subdistrict/village coverage. The body's census identifier
is separate from its LGD code.

## Row identity and conversion

Both State Name header spellings are accepted.

The reported record key is:

```text
(local_body_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 2 | `local_body_version` | `INTEGER` | `Local Body Version` | No |
| 3 | `local_body_name` | `VARCHAR` | `Local Body Name (In English)` | No |
| 4 | `local_body_name_local` | `VARCHAR` | `Local Body Name (In Local)` | No |
| 5 | `local_body_type_code` | `VARCHAR` | `Localbody Type Code` | No |
| 6 | `local_body_census_2011_code` | `VARCHAR` | `Census 2011 Code` | No |
| 7 | `state_code` | `VARCHAR` | `State Code` | No |
| 8 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
