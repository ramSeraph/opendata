# invalidated_census_villages

This report lists villages that LGD reports as invalidated, with
village/state codes and names and, where supplied, 2001/2011 census
references. It is a reported status list rather than a dated
invalidation-event log: the first observation of a row does not
establish when invalidation occurred.

The retained history contains one state-only placeholder with no village or
census attributes. It remains reporting context; exclude blank village codes
when counting villages. The record key is `village_code`; state remains an
attribute and filter.
Use the LGD village code, not a census number, when comparing with
[villages](villages.md).

## API

```python
from lgd_query.queries import invalidated_census_villages

rows = invalidated_census_villages.list(db).fetchall()
matches = invalidated_census_villages.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2001, 2011 for the primary entity only.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `village_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `village_code` | Integer or ASCII digit string; zeros preserved |
| `village_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |
| `village_census_2001_code` | Integer or ASCII digit string; zeros preserved |
| `village_census_2011_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query invalidated_census_villages list --format json
lgd-query invalidated_census_villages search NAME --mode fuzzy --cache-dir ./data
lgd-query invalidated_census_villages code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/invalidated_census_villages.md) and [shared query rules](../QUERIES.md).
