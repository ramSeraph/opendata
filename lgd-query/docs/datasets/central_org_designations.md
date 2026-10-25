# central_org_designations

This report lists designation titles within central organizations,
including English/local names and reported levels, such as postal
roles at different office levels. It describes titles rather than
named office-holders or individual office staffing.

A designation can occur at several levels; level names remain part
of the association's identity, including when level codes are blank.
There are no state columns. Organization references connect to
[central_orgs](central_orgs.md), while office membership is reported
separately in [central_org_units](central_org_units.md).

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## Row identity

The normalized key is `(designation_code, organization_level_code, organization_level_name)`.
Organization remain attributes and optional filters.
`by_code` can return several level associations for one designation code;
use level filters to select an association. Blank level codes remain a source
limitation described in the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/central_org_designations.md).

## API

```python
from lgd_query.queries import central_org_designations

rows = central_org_designations.list(db).fetchall()
matches = central_org_designations.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `designation_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `designation_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `designation_name` | Supplied `designation_name` | None |
| `designation_name_local` | Supplied `designation_name_local` | None |
| `organization_level_name` | Supplied `organization_level_name` | None |
| `organization_name` | Supplied `organization_name` | None |
| `english` | Supplied `designation_name` | None |
| `local` | Supplied `designation_name_local` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `designation_code` | Integer or ASCII digit string; zeros preserved |
| `designation_name` | Exact string |
| `designation_name_local` | Exact string |
| `organization_level_code` | Integer or ASCII digit string; zeros preserved |
| `organization_level_name` | Exact string |
| `organization_code` | Integer or ASCII digit string; zeros preserved |
| `organization_name` | Exact string |

## CLI

```sh
lgd-query central_org_designations list --format json
lgd-query central_org_designations search NAME --mode fuzzy --cache-dir ./data
lgd-query central_org_designations code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/central_org_designations.md) and [shared query rules](../QUERIES.md).
