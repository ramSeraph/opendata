# gp_mapping

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/gp_mapping.md) · [API/CLI conventions](../QUERIES.md)

This report links villages to gram panchayats/local bodies and
supplies their administrative and census context. Each association
is identified by `(village_code, local_body_code)`. A village can have
more than one local-body link; state, district and subdistrict are
attributes of the reported association.

## API

- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2001, 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `village_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `village_code`, `local_body_code`, `subdistrict_code`, `district_code`, `state_code`, `village_census_2011_code`, `village_census_2001_code`, `subdistrict_census_2011_code`, `subdistrict_census_2001_code`, `district_census_2011_code`, `district_census_2001_code` |
| Text | `village_name`, `local_body_name`, `subdistrict_name`, `district_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query gp_mapping list --village-code 626704
```
