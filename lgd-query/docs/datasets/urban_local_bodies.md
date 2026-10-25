# urban_local_bodies

LGD's urban local-body register supplies a body's LGD code, names,
version, type, state and census identifier. Each row identifies one
body by `local_body_code`. The type code/name classifies the body;
it does not describe a tier in the PRI hierarchy.

Use [urban_local_body_wards](urban_local_body_wards.md) for its wards
and [statewise_ulbs_coverage](statewise_ulbs_coverage.md) for reported
district/subdistrict/village coverage. The body's census identifier
is separate from its LGD code.

## API

```python
from lgd_query.queries import urban_local_bodies

rows = urban_local_bodies.list(db).fetchall()
matches = urban_local_bodies.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.
- `by_census_code(db, value, year=..., **filters)` supports 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_name_local` | Supplied `local_body_name_local` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |
| `local` | Supplied `local_body_name_local` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_version` | Nonnegative integer |
| `local_body_name` | Exact string |
| `local_body_name_local` | Exact string |
| `local_body_type_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query urban_local_bodies list --format json
lgd-query urban_local_bodies search NAME --mode fuzzy --cache-dir ./data
lgd-query urban_local_bodies code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/urban_local_bodies.md) and [shared query rules](../QUERIES.md).
