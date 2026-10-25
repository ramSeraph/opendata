# changes

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/changes.md) · [API/CLI conventions](../QUERIES.md)

The discontinued LGD change report records entity type/code,
version, names, census reference, operation and reported date. It
supplies structured entity references and retains every source row,
including duplicate or repeated claims; the report serial is not a
stable event identifier.

## API

- `by_code(db, code, **filters)` selects `entity_code` exactly and retains all matches.
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

| Value type | Filters |
| --- | --- |
| Text | `report_serial`, `entity_type`, `entity_name`, `entity_name_local`, `operation_name` |
| Code | `entity_code` |
| Integer | `entity_version` |
| Text, including source sentinels such as `null` | `census_code` |
| Date | `report_date`, `since`, `until` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query changes code 123 --entity-type Village --since 2024-01-01
```
