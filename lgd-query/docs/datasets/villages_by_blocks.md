# villages_by_blocks

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/villages_by_blocks.md) · [API/CLI conventions](../QUERIES.md)

This report associates villages with development blocks and, where
supplied, local bodies. It includes village administrative paths and
census references. Distinct block/body associations remain separate:
even the same village and local body can be reported under several
blocks. Row counts therefore need not count distinct villages.

## API

- `list(db, **filters)` retains every matching normalized association.
- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `block_name` | Supplied `block_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `village_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `village_code`, `block_code`, `local_body_code`, `subdistrict_code`, `district_code`, `state_code`, `village_census_2011_code`, `subdistrict_census_2011_code`, `district_census_2011_code`, `state_census_2011_code`, `local_body_census_2011_code` |
| Text | `village_name`, `block_name`, `local_body_name`, `subdistrict_name`, `district_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query villages_by_blocks list --block-code 170
```
