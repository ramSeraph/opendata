# district_panchayats

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/district_panchayats.md) · [API/CLI conventions](../QUERIES.md)

This report connects district panchayats to administrative districts,
supplying both codes/names and the state. A panchayat can be linked to
several districts, and a district can be linked to several panchayats.
The association is identified by
`(district_panchayat_code, district_code)`; state is an attribute.

## API

- `by_code(db, code, **filters)` selects `district_panchayat_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `district_panchayat_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `district_panchayat_name` | Supplied `district_panchayat_name` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `district_panchayat_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `district_panchayat_code`, `district_code`, `state_code` |
| Text | `district_panchayat_name`, `district_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query district_panchayats list --state-code 32
```
