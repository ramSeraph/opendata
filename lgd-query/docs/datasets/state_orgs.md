# state_orgs

This directory identifies state departments and organizations by
`organization_code`, with names, organization type, state and reported
parent organization. State is an attribute. The parent may appear
only as a reference, so the directory need not contain a row for every
parent in the hierarchy.

Offices belonging to these organizations are reported separately in
[state_org_units](state_org_units.md). Administrative level definitions
in [state_admin_depts](state_admin_depts.md) describe a different
concept despite that dataset's filename.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

```python
from lgd_query.queries import state_orgs

rows = state_orgs.list(db).fetchall()
matches = state_orgs.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `organization_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `organization_name` | Supplied `organization_name` | None |
| `parent_organization_name` | Supplied `parent_organization_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `organization_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `organization_code` | Integer or ASCII digit string; zeros preserved |
| `organization_name` | Exact string |
| `organization_type` | Exact string |
| `parent_organization_code` | Integer or ASCII digit string; zeros preserved |
| `parent_organization_name` | Exact string |
| `parent_organization_type` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query state_orgs list --format json
lgd-query state_orgs search NAME --mode fuzzy --cache-dir ./data
lgd-query state_orgs code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/state_orgs.md) and [shared query rules](../QUERIES.md).
