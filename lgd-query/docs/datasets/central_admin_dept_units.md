# central_admin_dept_units

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/central_admin_dept_units.md) · [API/CLI conventions](../QUERIES.md)

This report lists named central administrative units and their
administrative levels, including individual postal units, with
English/local names. The source's “Admin Department Code” becomes
`administrative_unit_level_code`, referencing
[central_admin_depts](central_admin_depts.md). There are no state columns.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

The record key is `administrative_unit_code`. The level code/name remain
attributes and filters; `administrative_unit_level_code` joins the corresponding
[central administrative-level register](central_admin_depts.md). A level change
versions the unit in history rather than creating another unit identity.

## API

- `by_code(db, code, **filters)` selects `administrative_unit_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `administrative_unit_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `administrative_unit_name` | Supplied `administrative_unit_name` | None |
| `administrative_unit_name_local` | Supplied `administrative_unit_name_local` | None |
| `administrative_unit_level_name` | Supplied `administrative_unit_level_name` | None |
| `english` | Supplied `administrative_unit_name` | None |
| `local` | Supplied `administrative_unit_name_local` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `administrative_unit_code`, `administrative_unit_level_code` |
| Text | `administrative_unit_name`, `administrative_unit_name_local`, `administrative_unit_level_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query central_admin_dept_units list --administrative-unit-level-code 1254
```
