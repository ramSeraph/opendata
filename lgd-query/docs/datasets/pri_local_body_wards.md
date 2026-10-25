# pri_local_body_wards

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/pri_local_body_wards.md) · [API/CLI conventions](../QUERIES.md)

LGD's PRI-ward report supplies ward codes, names and numbers, plus
the local body, state, body type and higher-parent names. Normalized
identity is `ward_code`; spelling variants and contradictory parent
labels do not create additional wards.

The [normalization and exclusion rules](../../../lgd/parquet/datasets/pri_local_body_wards.md#row-identity-and-conversion)
explain how these records are handled and where the original labels are retained.

The helper uses normalized fields without extra views. Older published
generations can still contain raw variants; queries return every match
rather than silently hiding them.

## API

- `by_code(db, code, **filters)` selects `ward_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `ward_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `ward_name` | Supplied `ward_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `state_name` | Supplied `state_name` | None |
| `ward_name_local` | Supplied `ward_name_local` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `district_panchayat_name` | Supplied `district_panchayat_name` | None |
| `intermediate_panchayat_name` | Supplied `intermediate_panchayat_name` | None |
| `english` | Supplied `ward_name` | None |
| `local` | Supplied `ward_name_local` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `ward_code`, `local_body_code`, `state_code` |
| Text | `ward_number`, `ward_name`, `local_body_name`, `state_name`, `ward_name_local`, `local_body_type_name`, `district_panchayat_name`, `intermediate_panchayat_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query pri_local_body_wards code 100113
```
