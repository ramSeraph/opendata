# tlb_villages

This is LGD's Gram Panchayat/TLB village-mapping report. It contains
both PRI gram panchayats and traditional local bodies, with village,
block, administrative-path and census references. The retained name
`tlb_villages` does not restrict the rows to traditional bodies.

Resolve body codes against both [pri_local_bodies](pri_local_bodies.md)
and [traditional_local_bodies](traditional_local_bodies.md). Supplied
body type codes/names classify the body, while block and village codes
identify separate entities. The misleading source body-census field
is omitted from normalized output; the state, district, subdistrict
and village census fields remain.

For example, Pohane (`183238`) and Wathephal (`184413`) are PRI village
panchayats in this report. The helper searches supplied names without an
implicit body-register join. See the
[scope and identifier notes](../../../lgd/parquet/datasets/tlb_villages.md#scope-and-local-body-identifiers).

`by_census_code` selects the village's census code; the omitted body-census
field is not a query filter.

## API

```python
from lgd_query.queries import tlb_villages

rows = tlb_villages.list(db).fetchall()
matches = tlb_villages.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
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

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `village_code` | Integer or ASCII digit string; zeros preserved |
| `village_name` | Exact string |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `local_body_type_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_type_name` | Exact string |
| `block_code` | Integer or ASCII digit string; zeros preserved |
| `block_name` | Exact string |
| `subdistrict_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_name` | Exact string |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |
| `state_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `district_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `village_census_2011_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query tlb_villages list --format json
lgd-query tlb_villages search NAME --mode fuzzy --cache-dir ./data
lgd-query tlb_villages code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/tlb_villages.md) and [shared query rules](../QUERIES.md).
