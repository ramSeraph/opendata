# statewise_ulbs_coverage

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/statewise_ulbs_coverage.md) · [API/CLI conventions](../QUERIES.md)

This report links urban local bodies to reported district,
subdistrict and village coverage. It includes both complete village
paths and district/subdistrict-only rows. The association key retains
`(local_body_code, district_code, subdistrict_code, village_code)`;
body/village alone cannot distinguish paths with missing lower levels.

## API

- `by_code(db, code, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `district_name` | Supplied `district_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `village_name` | Supplied `village_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `local_body_code`, `district_code`, `subdistrict_code`, `village_code`, `local_body_census_2011_code` |
| Text | `local_body_name`, `district_name`, `subdistrict_name`, `village_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query statewise_ulbs_coverage list --local-body-code 248111
```
