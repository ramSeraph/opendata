# state_admin_dept_units

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/state_admin_dept_units.md) · [API/CLI conventions](../QUERIES.md)

This report lists named state administrative units and the level
to which each belongs, with English/local names and state context.
`administrative_unit_code` identifies the reported unit, while
`administrative_unit_level_code` references a definition in
[state_admin_depts](state_admin_depts.md).

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

The record key is `administrative_unit_code`. Level and state remain attributes
and filters. `administrative_unit_level_code` joins the corresponding
[state administrative-level register](state_admin_depts.md); a reported level
or state change versions the same unit in history.

## API

- `by_code(db, code, **filters)` selects `administrative_unit_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `administrative_unit_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `administrative_unit_name` | Supplied `administrative_unit_name` | None |
| `administrative_unit_name_local` | Supplied `administrative_unit_name_local` | None |
| `administrative_unit_level_name` | Supplied `administrative_unit_level_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `administrative_unit_name` | None |
| `local` | Supplied `administrative_unit_name_local` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `administrative_unit_code`, `administrative_unit_level_code`, `state_code` |
| Text | `administrative_unit_name`, `administrative_unit_name_local`, `administrative_unit_level_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query state_admin_dept_units list --administrative-unit-level-code 1254
```
