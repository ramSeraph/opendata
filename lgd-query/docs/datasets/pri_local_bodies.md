# pri_local_bodies

The Panchayati Raj Institutions (PRI) register identifies local
bodies by `local_body_code` and supplies their names, version, type,
state and immediate parent code. In this report, type codes `1`, `2`
and `3` denote district, intermediate/block and village panchayats.

The reported name of each type varies by state and remains as supplied.
A top-level body can have a blank parent.
Parent codes support hierarchy lookups within the register, while
[district_panchayats](district_panchayats.md) supplies links to
administrative districts. A block panchayat's local-body code is
distinct from a development-block code.

See [the state-by-state type names](../../../lgd/parquet/datasets/pri_local_bodies.md#local-body-types-and-state-names)
for the labels reported at each level. Use the type code to filter a level
and retain `local_body_type_name` as supplied.

## API

```python
from lgd_query.queries import pri_local_bodies

rows = pri_local_bodies.list(db).fetchall()
matches = pri_local_bodies.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_name_local` | Supplied `local_body_name_local` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |
| `local` | Supplied `local_body_name_local` | None |
| `parent_local_body_name` | `pri_local_bodies.local_body_name` | `pri_local_bodies` (same report) |

Lookup keys are explicit and names never serve as join keys:

- `parent_local_body_name`: `parent_local_body_code` → `pri_local_bodies.local_body_code`, `state_code` → `pri_local_bodies.state_code`.

Lookup searches add `lookup_names` containing all distinct resolved labels. Multiple labels do not multiply the source row. Missing references do not match. The matching report can have a different date; inspect `queries.sources(...)` before opening it. Supplied columns remain unchanged.

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_version` | Nonnegative integer |
| `local_body_name` | Exact string |
| `local_body_name_local` | Exact string |
| `local_body_type_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_type_name` | Exact string |
| `parent_local_body_code` | Integer or ASCII digit string; zeros preserved |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query pri_local_bodies list --format json
lgd-query pri_local_bodies search NAME --mode fuzzy --cache-dir ./data
lgd-query pri_local_bodies code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/pri_local_bodies.md) and [shared query rules](../QUERIES.md).
