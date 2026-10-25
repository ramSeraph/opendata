# transactions

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/transactions.md) · [API/CLI conventions](../QUERIES.md)

LGD's newer cumulative event report supplies transaction ID,
operation code/name, date, state scope and a description. Descriptions
are free text that can mention several entities; the report does not
provide those mentions as structured entity relationships. State
scope `0` can describe the Centre.

## API

- `by_id(db, transaction_id, **filters)` selects `transaction_id` exactly and retains all matches.
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

| Value type | Filters |
| --- | --- |
| Text | `transaction_id`, `operation_name`, `description`, `state_name` |
| Code | `operation_code`, `state_code` |
| Date | `transaction_date`, `since`, `until` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query transactions search renamed --since 2024-01-01
```

`search` matches free-text descriptions by default. It does not extract a structured entity list or infer entity codes. IDs must be strings.
