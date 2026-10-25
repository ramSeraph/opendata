# changes

The discontinued LGD change report records entity type/code,
version, names, census reference, operation and reported date. It
supplies structured entity references and retains every source row,
including duplicate or repeated claims; the report serial is not a
stable event identifier.

This is one cumulative event table, not a sequence of entity snapshots.
Its row-date range does not prove complete collection coverage. The
newer [transactions](transactions.md) report has a different schema
and cannot be treated as the same event stream under renamed fields.

## API

```python
from lgd_query.queries import changes

rows = changes.list(db).fetchall()
matches = changes.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `entity_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `entity_name`.

`entity_type` is required whenever filtering or looking up `entity_code`; numeric codes alone do not identify the namespace.

`since` and `until` are inclusive `report_date` bounds (ISO date strings or `datetime.date`). Duplicate rows/IDs remain separate events.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `entity_name` | Supplied `entity_name` | None |
| `entity_name_local` | Supplied `entity_name_local` | None |
| `operation_name` | Supplied `operation_name` | None |
| `english` | Supplied `entity_name` | None |
| `local` | Supplied `entity_name_local` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `report_serial` | Exact string |
| `entity_type` | Exact string |
| `entity_code` | Integer or ASCII digit string; zeros preserved |
| `entity_version` | Nonnegative integer |
| `entity_name` | Exact string |
| `entity_name_local` | Exact string |
| `census_code` | Exact source text, including sentinels such as `null` |
| `operation_name` | Exact string |
| `report_date` | ISO date string or `datetime.date` |
| `since` | ISO date string or `datetime.date` |
| `until` | ISO date string or `datetime.date` |

## CLI

```sh
lgd-query changes list --format json
lgd-query changes search NAME --mode fuzzy --cache-dir ./data
lgd-query changes code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/changes.md) and [shared query rules](../QUERIES.md).
