# villages

LGD's village register includes English/local names, version,
state/district/subdistrict references, census identifiers and, where
supplied, status, category and remarks. A row represents a
`village_code`/`village_category` pair: the same village can have several
reported categories. Count distinct village codes when counting places.

The parent codes connect to the administrative registers. Block and
local-body associations are supplied separately by reports such as
[villages_by_blocks](villages_by_blocks.md) and [gp_mapping](gp_mapping.md).
Status and category retain the source's claims; they are not inferred
from membership in a mapping report.

## API

```python
from lgd_query.queries import villages

rows = villages.list(db).fetchall()
matches = villages.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2001, 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `village_name_local` | Supplied `village_name_local` | None |
| `state_name` | Supplied `state_name` | None |
| `district_name` | Supplied `district_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `english` | Supplied `village_name` | None |
| `local` | Supplied `village_name_local` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `village_code` | Integer or ASCII digit string; zeros preserved |
| `village_version` | Nonnegative integer |
| `village_name` | Exact string |
| `village_name_local` | Exact string |
| `village_status` | Exact string |
| `village_category` | Exact string |
| `remark` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `subdistrict_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_name` | Exact string |
| `village_census_2001_code` | Integer or ASCII digit string; zeros preserved |
| `village_census_2011_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query villages list --format json
lgd-query villages search NAME --mode fuzzy --cache-dir ./data
lgd-query villages code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/villages.md) and [shared query rules](../QUERIES.md).
