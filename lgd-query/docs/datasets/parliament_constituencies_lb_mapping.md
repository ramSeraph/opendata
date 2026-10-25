# parliament_constituencies_lb_mapping

This report links parliamentary constituencies to named
assembly constituencies and local bodies, with a body-type name,
state and coverage flag. The parliamentary reference is coded; assembly
and local-body references are names. Those names identify reported
associations here and cannot safely be converted to unique LGD codes
from spelling alone.

State and full/partial coverage are attributes. Simultaneous `F`/`P`
claims become one association with NULL coverage, with both originals
recoverable; literal blank coverage remains blank. The retained historical
collection ends in December 2022. The scraper has been restored for current
reports; inspect each export's source date. The collection gap does not
establish that the links stayed unchanged.

The normalized key is `(parliament_constituency_code, assembly_constituency_name,
local_body_name, local_body_type_name)`. Exact `coverage_type='F'` or `'P'`
filters exclude unresolved associations; use SQL `coverage_type IS NULL`
to select them, or `coverage_type = ''` for literal blank coverage.

## API

```python
from lgd_query.queries import parliament_constituencies_lb_mapping

rows = parliament_constituencies_lb_mapping.list(db).fetchall()
matches = parliament_constituencies_lb_mapping.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `parliament_constituency_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `parliament_constituency_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `parliament_constituency_name` | Supplied `parliament_constituency_name` | None |
| `assembly_constituency_name` | Supplied `assembly_constituency_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `english` | Supplied `parliament_constituency_name` | None |
| `state_name` | `states.state_name` | `states` |

Lookup keys are explicit and names never serve as join keys:

- `state_name`: `state_code` → `states.state_code`.

Lookup searches add `lookup_names` containing all distinct resolved labels. Multiple labels do not multiply the source row. Missing references do not match. The matching report can have a different date; inspect `queries.sources(...)` before opening it. Supplied columns remain unchanged.

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `parliament_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `parliament_constituency_name` | Exact string |
| `assembly_constituency_name` | Exact string |
| `local_body_name` | Exact string |
| `local_body_type_name` | Exact string |
| `coverage_type` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query parliament_constituencies_lb_mapping list --format json
lgd-query parliament_constituencies_lb_mapping search NAME --mode fuzzy --cache-dir ./data
lgd-query parliament_constituencies_lb_mapping code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/parliament_constituencies_lb_mapping.md) and [shared query rules](../QUERIES.md).
