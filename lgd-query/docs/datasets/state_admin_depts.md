# state_admin_depts

Despite its filename, this report defines administrative-unit
levels, not a directory of departments. It supplies level codes/names,
a parent administrative reference, state and optional source metadata
about hierarchy, publication and activity. The level code identifies
the record; state remains an attribute.

[state_admin_dept_units](state_admin_dept_units.md) lists the named
administrative units at those levels. Organizations themselves are
in [state_orgs](state_orgs.md). Administrative levels, administrative
units and organization offices use different identifiers and must
not be equated because their names or numbers match.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

```python
from lgd_query.queries import state_admin_depts

rows = state_admin_depts.list(db).fetchall()
matches = state_admin_depts.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `administrative_unit_level_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `administrative_unit_level_name`.

The normalized key is `administrative_unit_level_code`. `state_code` remains an
optional filter and supplies context when comparing this report with other
datasets. It is not part of this dataset's row identity.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `administrative_unit_level_name` | Supplied `administrative_unit_level_name` | None |
| `administrative_unit_level_name_local` | Supplied `administrative_unit_level_name_local` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `administrative_unit_level_name` | None |
| `local` | Supplied `administrative_unit_level_name_local` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `administrative_unit_level_code` | Integer or ASCII digit string; zeros preserved |
| `administrative_unit_level_name` | Exact string |
| `parent_administrative_code` | Signed integer or exact integer text |
| `organization_level_code` | Integer or ASCII digit string; zeros preserved |
| `administrative_unit_level_name_local` | Exact string |
| `created_by` | Exact string |
| `created_on` | Exact string |
| `hierarchy` | Exact string |
| `is_active` | Exact string |
| `publication_status` | Exact string |
| `local_body_level` | Exact string |
| `organization_located_at_levels` | Exact string |
| `overlap_unit` | Exact string |
| `parent_category` | Exact string |
| `parent_organization_level_code` | Integer or ASCII digit string; zeros preserved |
| `revenue_entity` | Exact string |
| `unit_level_type` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query state_admin_depts list --format json
lgd-query state_admin_depts search NAME --mode fuzzy --cache-dir ./data
lgd-query state_admin_depts code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/state_admin_depts.md) and [shared query rules](../QUERIES.md).
