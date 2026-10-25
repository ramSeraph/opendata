# urban_local_bodies

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/urban_local_bodies.md) · [API/CLI conventions](../QUERIES.md)

LGD's urban local-body register supplies a body's LGD code, names,
version, type, state and census identifier. Each row identifies one
body by `local_body_code`. The type code/name classifies the body;
it does not describe a tier in the PRI hierarchy.

## API

- `by_code(db, code, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_name_local` | Supplied `local_body_name_local` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |
| `local` | Supplied `local_body_name_local` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `local_body_code`, `local_body_type_code`, `local_body_census_2011_code`, `state_code` |
| Integer | `local_body_version` |
| Text | `local_body_name`, `local_body_name_local`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query urban_local_bodies list --limit 5
```
