# pincode_villages

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/pincode_villages.md) · [API/CLI conventions](../QUERIES.md)

LGD's village/pincode report supplies village and postal-code
associations with state, district and subdistrict codes/names. The
normalized key is `(village_code, pincode)`; administrative parents
are attributes. Several pincodes can be associated with one village.

## API

- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `village_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `village_code`, `subdistrict_code`, `district_code`, `state_code` |
| Text | `village_name`, `pincode`, `subdistrict_name`, `district_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query pincode_villages list --pincode 691001
```
