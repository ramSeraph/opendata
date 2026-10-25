# pri_local_bodies

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/pri_local_bodies.md) · [API/CLI conventions](../QUERIES.md)

The Panchayati Raj Institutions (PRI) register identifies local
bodies by `local_body_code` and supplies their names, version, type,
state and immediate parent code. In this report, type codes `1`, `2`
and `3` denote district, intermediate/block and village panchayats.

See [the state-by-state type names](../../../lgd/parquet/datasets/pri_local_bodies.md#local-body-types-and-state-names)
for the labels reported at each level. Use the type code to filter a level
and retain `local_body_type_name` as supplied.

## API

- `by_code(db, code, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_name_local` | Supplied `local_body_name_local` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |
| `local` | Supplied `local_body_name_local` | None |
| `parent_local_body_name` | `pri_local_bodies.local_body_name` | `pri_local_bodies` (same report) |

Lookup keys are explicit and names never serve as join keys:

- `parent_local_body_name`: `parent_local_body_code` → `pri_local_bodies.local_body_code`, `state_code` → `pri_local_bodies.state_code`.

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `local_body_code`, `local_body_type_code`, `parent_local_body_code`, `state_code` |
| Integer | `local_body_version` |
| Text | `local_body_name`, `local_body_name_local`, `local_body_type_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query pri_local_bodies search NAME --field parent_local_body_name
```
