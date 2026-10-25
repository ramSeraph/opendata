# blocks

LGD's development-block register contains block codes, names,
versions and reported district/state references. Each row represents
a block/district association. A block can appear against several
districts, so row counts and distinct `block_code` counts differ.

Use this report for the block's district associations and
[villages_by_blocks](villages_by_blocks.md) for its reported village
links. Block codes, subdistrict codes and panchayat codes identify
different entities, even where their names or numbers resemble one another.

## API

```python
from lgd_query.queries import blocks

rows = blocks.list(db).fetchall()
matches = blocks.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `block_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `block_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `block_name` | Supplied `block_name` | None |
| `block_name_local` | Supplied `block_name_local` | None |
| `district_name` | Supplied `district_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `block_name` | None |
| `local` | Supplied `block_name_local` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `block_code` | Integer or ASCII digit string; zeros preserved |
| `block_version` | Nonnegative integer |
| `block_name` | Exact string |
| `block_name_local` | Exact string |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query blocks list --format json
lgd-query blocks search NAME --mode fuzzy --cache-dir ./data
lgd-query blocks code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/blocks.md) and [shared query rules](../QUERIES.md).
