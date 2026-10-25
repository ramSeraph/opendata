# gp_mapping

This report links villages to gram panchayats/local bodies and
supplies their administrative and census context. Each association
is identified by `(village_code, local_body_code)`. A village can have
more than one local-body link; state, district and subdistrict are
attributes of the reported association.

Resolve village and body references through [villages](villages.md)
and [pri_local_bodies](pri_local_bodies.md). Rows that identify a
village but supply no body remain as incomplete evidence. Rows with
no village and only hierarchy context are omitted after validation,
so they do not appear as fictitious village/body associations.

## API

```python
from lgd_query.queries import gp_mapping

rows = gp_mapping.list(db).fetchall()
matches = gp_mapping.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, value, year=..., **filters)` supports 2001, 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `village_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `village_code` | Integer or ASCII digit string; zeros preserved |
| `village_name` | Exact string |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `subdistrict_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_name` | Exact string |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |
| `village_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `village_census_2001_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_census_2001_code` | Integer or ASCII digit string; zeros preserved |
| `district_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `district_census_2001_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query gp_mapping list --format json
lgd-query gp_mapping search NAME --mode fuzzy --cache-dir ./data
lgd-query gp_mapping code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/gp_mapping.md) and [shared query rules](../QUERIES.md).
