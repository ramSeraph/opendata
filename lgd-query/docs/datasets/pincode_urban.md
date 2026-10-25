# pincode_urban

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/pincode_urban.md) · [API/CLI conventions](../QUERIES.md)

LGD's urban-body/pincode report supplies local-body and postal-code
associations with body and state names/codes. A body may have several
pincodes. The record key is `(local_body_code, pincode)`; state code/name
remain attributes and filters.

## API

- `by_code(db, code, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `local_body_code`, `state_code` |
| Text | `local_body_name`, `local_body_type_name`, `pincode`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query pincode_urban list --pincode 691001
```
