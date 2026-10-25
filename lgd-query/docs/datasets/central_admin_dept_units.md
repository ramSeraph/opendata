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

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

The record key is `administrative_unit_code`. The level code/name remain
attributes and filters; `administrative_unit_level_code` joins the corresponding
[central administrative-level register](central_admin_depts.md). A level change
versions the unit in history rather than creating another unit identity.

## API

```python
from lgd_query.queries import central_admin_dept_units

rows = central_admin_dept_units.list(db).fetchall()
matches = central_admin_dept_units.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `administrative_unit_code` exactly and retains all matches.
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

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `administrative_unit_code` | Integer or ASCII digit string; zeros preserved |
| `administrative_unit_name` | Exact string |
| `administrative_unit_name_local` | Exact string |
| `administrative_unit_level_code` | Integer or ASCII digit string; zeros preserved |
| `administrative_unit_level_name` | Exact string |

## CLI

```sh
lgd-query central_admin_dept_units list --format json
lgd-query central_admin_dept_units search NAME --mode fuzzy --cache-dir ./data
lgd-query central_admin_dept_units code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/central_admin_dept_units.md) and [shared query rules](../QUERIES.md).
