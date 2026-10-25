# nofn_panchayats

This retired report lists panchayats/local bodies in the National
Optical Fibre Network (NOFN) project, with body codes/names, state and
named district/subdistrict paths. It includes reported PRI and
traditional bodies. One body can have several named paths; district
and subdistrict codes are not supplied.

Membership does not establish operational fibre, service availability
or completeness of the local-body register. The retained source ends
in December 2024. Resolve bodies against the PRI and traditional
registers where possible, and retain unmatched parent names without
inventing codes.

Collection of this report will not resume in this project. The query helpers
remain available for retained historical Parquet files; a new daily report is
not expected. The CLI requires a release index that actually publishes such a
file, so these commands are not available through the current daily release.

## API

```python
from lgd_query.queries import nofn_panchayats

rows = nofn_panchayats.list(db).fetchall()
matches = nofn_panchayats.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `district_name` | Supplied `district_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `district_name` | Exact string |
| `subdistrict_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query nofn_panchayats list --format json
lgd-query nofn_panchayats search NAME --mode fuzzy --cache-dir ./data
lgd-query nofn_panchayats code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/nofn_panchayats.md) and [shared query rules](../QUERIES.md).
