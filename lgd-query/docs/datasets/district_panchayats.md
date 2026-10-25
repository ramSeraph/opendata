# district_panchayats

This report connects district panchayats to administrative districts,
supplying both codes/names and the state. A panchayat can be linked to
several districts, and a district can be linked to several panchayats.
The association is identified by
`(district_panchayat_code, district_code)`; state is an attribute.

Resolve the panchayat code as a local-body code in
[pri_local_bodies](pri_local_bodies.md), and the district code in
[districts](districts.md). The two identifiers describe different
institutions and need not form a one-to-one hierarchy.

## API

```python
from lgd_query.queries import district_panchayats

rows = district_panchayats.list(db).fetchall()
matches = district_panchayats.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `district_panchayat_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `district_panchayat_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `district_panchayat_name` | Supplied `district_panchayat_name` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `district_panchayat_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `district_panchayat_code` | Integer or ASCII digit string; zeros preserved |
| `district_panchayat_name` | Exact string |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query district_panchayats list --format json
lgd-query district_panchayats search NAME --mode fuzzy --cache-dir ./data
lgd-query district_panchayats code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/district_panchayats.md) and [shared query rules](../QUERIES.md).
