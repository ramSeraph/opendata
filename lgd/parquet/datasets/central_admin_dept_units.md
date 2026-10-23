# central_admin_dept_units

One reported administrative unit/administrative-level association. Admin Department Code is mapped to administrative_unit_level_code, distinguishing levels from units and organizations. Local-language names are retained. Collection gaps cannot be inferred from a single converted report. This central report has no state columns.

## Row identity and conversion

The reported record key is:

```text
(administrative_unit_code, administrative_unit_level_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

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
