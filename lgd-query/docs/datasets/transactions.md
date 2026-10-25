# transactions

LGD's newer cumulative event report supplies transaction ID,
operation code/name, date, state scope and a description. Descriptions
are free text that can mention several entities; the report does not
provide those mentions as structured entity relationships. State
scope `0` can describe the Centre.

Every reported row is retained, including repeated IDs and differing
descriptions. This is one event table without snapshot validity
intervals. Collection coverage is tracked separately from event dates,
and the earlier [changes](changes.md) report remains a separate dataset.

## API

```python
from lgd_query.queries import transactions

rows = transactions.list(db).fetchall()
matches = transactions.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_id(db, value, **filters)` selects `transaction_id` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `description`.

`since` and `until` are inclusive `transaction_date` bounds (ISO date strings or `datetime.date`). Duplicate rows/IDs remain separate events.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `operation_name` | Supplied `operation_name` | None |
| `description` | Supplied `description` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `description` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `transaction_id` | Exact string |
| `operation_code` | Integer or ASCII digit string; zeros preserved |
| `operation_name` | Exact string |
| `description` | Exact string |
| `transaction_date` | ISO date string or `datetime.date` |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |
| `since` | ISO date string or `datetime.date` |
| `until` | ISO date string or `datetime.date` |

## CLI

```sh
lgd-query transactions list --format json
lgd-query transactions search NAME --mode fuzzy --cache-dir ./data
lgd-query transactions id CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

`search` matches free-text descriptions by default. It does not extract a structured entity list or infer entity codes. IDs must be strings.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/transactions.md) and [shared query rules](../QUERIES.md).
