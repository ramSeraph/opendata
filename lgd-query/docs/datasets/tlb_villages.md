# tlb_villages

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/tlb_villages.md) · [API/CLI conventions](../QUERIES.md)

This is LGD's Gram Panchayat/TLB village-mapping report. It contains
both PRI gram panchayats and traditional local bodies, with village,
block, administrative-path and census references. The retained name
`tlb_villages` does not restrict the rows to traditional bodies.

For example, Pohane (`183238`) and Wathephal (`184413`) are PRI village
panchayats in this report. The helper searches supplied names without an
implicit body-register join. See the
[scope and identifier notes](../../../lgd/parquet/datasets/tlb_villages.md#scope-and-local-body-identifiers).

`by_census_code` selects the village's census code; the omitted body-census
field is not a query filter.

## API

- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `block_name` | Supplied `block_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `village_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `village_code`, `local_body_code`, `local_body_type_code`, `block_code`, `subdistrict_code`, `district_code`, `state_code`, `state_census_2011_code`, `district_census_2011_code`, `subdistrict_census_2011_code`, `village_census_2011_code` |
| Text | `village_name`, `local_body_name`, `local_body_type_name`, `block_name`, `subdistrict_name`, `district_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query tlb_villages list --state-code 16
```
