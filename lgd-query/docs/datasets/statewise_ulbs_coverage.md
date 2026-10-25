# statewise_ulbs_coverage

This report links urban local bodies to reported district,
subdistrict and village coverage. It includes both complete village
paths and district/subdistrict-only rows. The association key retains
`(local_body_code, district_code, subdistrict_code, village_code)`;
body/village alone cannot distinguish paths with missing lower levels.

A body can have several geographic associations. Blank or zero child
references do not identify a village. The report supplies state names
without state codes; conversion does not invent those codes or infer
ward locations from body-level coverage.

## API

```python
from lgd_query.queries import statewise_ulbs_coverage

rows = statewise_ulbs_coverage.list(db).fetchall()
matches = statewise_ulbs_coverage.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.
- `by_census_code(db, value, year=..., **filters)` supports 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `district_name` | Supplied `district_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `village_name` | Supplied `village_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `subdistrict_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_name` | Exact string |
| `village_code` | Integer or ASCII digit string; zeros preserved |
| `village_name` | Exact string |
| `state_name` | Exact string |
| `local_body_census_2011_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query statewise_ulbs_coverage list --format json
lgd-query statewise_ulbs_coverage search NAME --mode fuzzy --cache-dir ./data
lgd-query statewise_ulbs_coverage code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/statewise_ulbs_coverage.md) and [shared query rules](../QUERIES.md).
