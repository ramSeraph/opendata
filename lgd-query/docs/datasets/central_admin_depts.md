# central_admin_depts

Despite its filename, this report defines central administrative-unit
levels, including named postal levels, rather than listing departments.
It supplies level codes/names, parent administrative references and
optional hierarchy/publication/activity metadata. It has no state
columns.

[central_admin_dept_units](central_admin_dept_units.md) lists named
units belonging to these levels. The separate
[central_orgs](central_orgs.md) and [central_org_units](central_org_units.md)
reports describe organizations and offices; matching names or numbers
do not establish a shared identifier namespace.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

```python
from lgd_query.queries import central_admin_depts

rows = central_admin_depts.list(db).fetchall()
matches = central_admin_depts.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `administrative_unit_level_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `administrative_unit_level_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `administrative_unit_level_name` | Supplied `administrative_unit_level_name` | None |
| `administrative_unit_level_name_local` | Supplied `administrative_unit_level_name_local` | None |
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

## CLI

```sh
lgd-query central_admin_depts list --format json
lgd-query central_admin_depts search NAME --mode fuzzy --cache-dir ./data
lgd-query central_admin_depts code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/central_admin_depts.md) and [shared query rules](../QUERIES.md).
