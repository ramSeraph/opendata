# central_orgs

This directory identifies central departments and organizations by
`organization_code`, with names, types and reported parent
organizations. It has no state columns. A parent ministry or
organization can appear only as a reference; conversion does not
synthesize a missing parent row.

[central_org_units](central_org_units.md) supplies their offices/units,
while [central_org_designations](central_org_designations.md) supplies
titles and levels. Parent references describe the hierarchy asserted
in the report and are not guaranteed to resolve within the directory.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

```python
from lgd_query.queries import central_orgs

rows = central_orgs.list(db).fetchall()
matches = central_orgs.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `organization_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `organization_name` | Supplied `organization_name` | None |
| `parent_organization_name` | Supplied `parent_organization_name` | None |
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

## CLI

```sh
lgd-query central_orgs list --format json
lgd-query central_orgs search NAME --mode fuzzy --cache-dir ./data
lgd-query central_orgs code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/central_orgs.md) and [shared query rules](../QUERIES.md).
