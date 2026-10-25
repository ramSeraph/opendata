# invalidated_census_villages

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/invalidated_census_villages.md) · [API/CLI conventions](../QUERIES.md)

This report lists villages that LGD reports as invalidated, with
village/state codes and names and, where supplied, 2001/2011 census
references. It is a reported status list rather than a dated
invalidation-event log: the first observation of a row does not
establish when invalidation occurred.

## API

- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2001, 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `village_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `village_code`, `state_code`, `village_census_2001_code`, `village_census_2011_code` |
| Text | `village_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query invalidated_census_villages list --is-blank village_code
```
