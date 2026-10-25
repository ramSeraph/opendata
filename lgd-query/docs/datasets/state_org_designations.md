# state_org_designations

This report lists designation titles within state organizations,
with English/local names and reported organization-level associations.
It describes posts or roles, not the people holding them or a staffing
assignment to a particular office.

One designation can be associated with several levels. Level codes
may be blank, and distinct level names are retained in record
identity. Organization and state provide context; join
[state_orgs](state_orgs.md) by organization code to inspect the parent
organization rather than matching a designation's name to an office.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## Row identity

The normalized key is `(designation_code, organization_level_code, organization_level_name)`.
Organization and state remain attributes and optional filters.
`by_code` can return several level associations for one designation code;
use level filters to select an association. Blank level codes remain a source
limitation described in the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/state_org_designations.md).

## API

```python
from lgd_query.queries import state_org_designations

rows = state_org_designations.list(db).fetchall()
matches = state_org_designations.search(db, "name", mode="contains").fetchall()
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
| `state_name` | Supplied `state_name` | None |
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
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query state_org_designations list --format json
lgd-query state_org_designations search NAME --mode fuzzy --cache-dir ./data
lgd-query state_org_designations code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/state_org_designations.md) and [shared query rules](../QUERIES.md).
