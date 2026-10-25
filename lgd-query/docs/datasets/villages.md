# villages

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/villages.md) · [API/CLI conventions](../QUERIES.md)

LGD's village register includes English/local names, version,
state/district/subdistrict references, census identifiers and, where
supplied, status, category and remarks. A row represents a
`village_code`/`village_category` pair: the same village can have several
reported categories. Count distinct village codes when counting places.

## API

- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2001, 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `village_name_local` | Supplied `village_name_local` | None |
| `state_name` | Supplied `state_name` | None |
| `district_name` | Supplied `district_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `english` | Supplied `village_name` | None |
| `local` | Supplied `village_name_local` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `village_code`, `state_code`, `district_code`, `subdistrict_code`, `village_census_2001_code`, `village_census_2011_code` |
| Integer | `village_version` |
| Text | `village_name`, `village_name_local`, `village_status`, `village_category`, `remark`, `state_name`, `district_name`, `subdistrict_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query villages search Rampur --state-code 9 --provenance
```
