# villages_by_blocks

This report associates villages with development blocks and, where
supplied, local bodies. It includes village administrative paths and
census references. Distinct block/body associations remain separate:
even the same village and local body can be reported under several
blocks. Row counts therefore need not count distinct villages.

`district_code` and `district_name` describe the village. The source's conflicting
block-district columns are omitted from normalized output; consult
[blocks](blocks.md) for reported block/district associations. Removing
those columns collapses duplicate assertions without discarding a
distinct village/block/local-body link.

## API

```python
from lgd_query.queries import villages_by_blocks

rows = villages_by_blocks.list(db).fetchall()
matches = villages_by_blocks.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching normalized association.
- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `block_name` | Supplied `block_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
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
| `block_code` | Integer or ASCII digit string; zeros preserved |
| `block_name` | Exact string |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `subdistrict_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_name` | Exact string |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |
| `village_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `district_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `state_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_census_2011_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query villages_by_blocks list --format json
lgd-query villages_by_blocks search NAME --mode fuzzy --cache-dir ./data
lgd-query villages_by_blocks code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/villages_by_blocks.md) and [shared query rules](../QUERIES.md).
