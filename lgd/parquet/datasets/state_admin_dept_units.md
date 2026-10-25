# state_admin_dept_units

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/state_admin_dept_units.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This report lists named state administrative units and the level
to which each belongs, with English/local names and state context.
`administrative_unit_code` identifies the reported unit, while
`administrative_unit_level_code` references a definition in
[state_admin_depts](state_admin_depts.md).

The source calls the level an “Admin Department”; it is neither the
unit's organization code nor an office identifier. Keep this report
separate from [state_org_units](state_org_units.md) unless an explicit
cross-reference supports a join. Historical collection gaps are
recorded separately and do not mean all units ceased to exist.

## Row identity and conversion

The reported record key is:

```text
(administrative_unit_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

Level and state remain attributes and join/filter fields. Across all 1,176
retained observations from 30 January 2022 through 24 October 2026, each of the
108,580 historical unit codes belongs to one reported level and state, with no
simultaneous conflicting rows. Neither field is needed to distinguish units.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `administrative_unit_code` | `VARCHAR` | `Admin Unit Entity Code` | No |
| 2 | `administrative_unit_name` | `VARCHAR` | `Admin Unit Entity Name` | No |
| 3 | `administrative_unit_name_local` | `VARCHAR` | `Admin Unit Entity Name (Local)` | No |
| 4 | `administrative_unit_level_code` | `VARCHAR` | `Admin Department Code` | No |
| 5 | `administrative_unit_level_name` | `VARCHAR` | `Admin Department Name` | No |
| 6 | `state_code` | `VARCHAR` | `State Code` | No |
| 7 | `state_name` | `VARCHAR` | `State Name` | No |
