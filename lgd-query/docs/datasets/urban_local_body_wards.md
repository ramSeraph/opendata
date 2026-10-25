# urban_local_body_wards

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/urban_local_body_wards.md) · [API/CLI conventions](../QUERIES.md)

LGD's urban-ward register identifies each ward by `ward_code` and
supplies its name, ward number, local-body code/name and state. The
body reference connects to [urban_local_bodies](urban_local_bodies.md).

## API

- `by_code(db, code, **filters)` selects `ward_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `ward_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `ward_name` | Supplied `ward_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `ward_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `ward_code`, `local_body_code`, `state_code`, `local_body_census_2011_code` |
| Text | `ward_number`, `ward_name`, `local_body_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query urban_local_body_wards list --local-body-code 248111
```
