# blocks

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/blocks.md) · [API/CLI conventions](../QUERIES.md)

LGD's development-block register contains block codes, names,
versions and reported district/state references. Each row represents
a block/district association. A block can appear against several
districts, so row counts and distinct `block_code` counts differ.

## API

- `by_code(db, code, **filters)` selects `block_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `block_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `block_name` | Supplied `block_name` | None |
| `block_name_local` | Supplied `block_name_local` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `block_name` | None |
| `local` | Supplied `block_name_local` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `block_code`, `district_code`, `state_code` |
| Integer | `block_version` |
| Text | `block_name`, `block_name_local`, `district_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query blocks list --state-code 32
```
