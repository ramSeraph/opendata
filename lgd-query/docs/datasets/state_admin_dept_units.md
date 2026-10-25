# state_admin_dept_units

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

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

The record key is `administrative_unit_code`. Level and state remain attributes
and filters. `administrative_unit_level_code` joins the corresponding
[state administrative-level register](state_admin_depts.md); a reported level
or state change versions the same unit in history.

## API

```python
from lgd_query.queries import state_admin_dept_units

rows = state_admin_dept_units.list(db).fetchall()
matches = state_admin_dept_units.search(db, "name", mode="contains").fetchall()
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
| `state_name` | Supplied `state_name` | None |
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
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query state_admin_dept_units list --format json
lgd-query state_admin_dept_units search NAME --mode fuzzy --cache-dir ./data
lgd-query state_admin_dept_units code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/state_admin_dept_units.md) and [shared query rules](../QUERIES.md).
