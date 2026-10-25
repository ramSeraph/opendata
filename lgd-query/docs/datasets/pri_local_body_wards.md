# pri_local_body_wards

LGD's PRI-ward report supplies ward codes, names and numbers, plus
the local body, state, body type and higher-parent names. Normalized
identity is `ward_code`; spelling variants and contradictory parent
labels do not create additional wards.

When source labels or state attributes conflict, conversion resolves
them by body code using a PRI register dated at or before the report.
Original variants remain in discrepancy evidence. Unresolved records
are omitted from the normalized daily report, with history able to
retain the previous reliable value as not updated. Reviewed stale
ward/body exclusions apply only within their documented date limits.

The [normalization and exclusion rules](../../../lgd/parquet/datasets/pri_local_body_wards.md#row-identity-and-conversion)
explain how these records are handled and where the original labels are retained.

The helper uses normalized fields without extra views. Older published
generations can still contain raw variants; queries return every match
rather than silently hiding them.

## API

```python
from lgd_query.queries import pri_local_body_wards

rows = pri_local_body_wards.list(db).fetchall()
matches = pri_local_body_wards.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `ward_code` exactly and retains all matches.
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

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `ward_code` | Integer or ASCII digit string; zeros preserved |
| `ward_number` | Exact string |
| `ward_name` | Exact string |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |
| `ward_name_local` | Exact string |
| `local_body_type_name` | Exact string |
| `district_panchayat_name` | Exact string |
| `intermediate_panchayat_name` | Exact string |

## CLI

```sh
lgd-query pri_local_body_wards list --format json
lgd-query pri_local_body_wards search NAME --mode fuzzy --cache-dir ./data
lgd-query pri_local_body_wards code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/pri_local_body_wards.md) and [shared query rules](../QUERIES.md).
