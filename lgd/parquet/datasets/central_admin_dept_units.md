# central_admin_dept_units

This report lists named central administrative units and their
administrative levels, including individual postal units, with
English/local names. The source's “Admin Department Code” becomes
`administrative_unit_level_code`, referencing
[central_admin_depts](central_admin_depts.md). There are no state columns.

`administrative_unit_code` is distinct from an
`organization_unit_code` in [central_org_units](central_org_units.md).
Similar names do not establish a code-level crosswalk. Historical
collection gaps are preserved separately from the observed unit list.

## Row identity and conversion

The reported record key is:

```text
(administrative_unit_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

The level code remains an attribute and a join/filter field. Across 1,184
retained observations from 30 January 2022 through 24 October 2026, all 67,036
unit codes have one reported level each and no simultaneous conflicting rows.
It is not needed to distinguish records.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `administrative_unit_code` | `VARCHAR` | `Admin Unit Entity Code` | No |
| 2 | `administrative_unit_name` | `VARCHAR` | `Admin Unit Entity Name` | No |
| 3 | `administrative_unit_name_local` | `VARCHAR` | `Admin Unit Entity Name (Local)` | No |
| 4 | `administrative_unit_level_code` | `VARCHAR` | `Admin Department Code` | No |
| 5 | `administrative_unit_level_name` | `VARCHAR` | `Admin Department Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
