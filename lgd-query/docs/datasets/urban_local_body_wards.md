# urban_local_body_wards

LGD's urban-ward register identifies each ward by `ward_code` and
supplies its name, ward number, local-body code/name and state. The
body reference connects to [urban_local_bodies](urban_local_bodies.md).

Ward numbers are source labels and are not interchangeable with ward
codes. This report does not supply district or subdistrict assignments.
Geographic paths in [constituencies_mapping_urban](constituencies_mapping_urban.md)
come from a separate report and cannot be verified against this register
alone. Any census code here belongs to the body.

## API

```python
from lgd_query.queries import urban_local_body_wards

rows = urban_local_body_wards.list(db).fetchall()
matches = urban_local_body_wards.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `ward_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `ward_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `ward_name` | Supplied `ward_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `ward_name` | None |

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
| `local_body_census_2011_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query urban_local_body_wards list --format json
lgd-query urban_local_body_wards search NAME --mode fuzzy --cache-dir ./data
lgd-query urban_local_body_wards code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/urban_local_body_wards.md) and [shared query rules](../QUERIES.md).
