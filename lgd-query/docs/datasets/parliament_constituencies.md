# parliament_constituencies

LGD's parliamentary-constituency register supplies each
`parliament_constituency_code`, its name and state code/name. The LGD
constituency code identifies the row; state is an attribute.

This register does not supply ECI constituency numbers. The PRI and
urban constituency-mapping reports supply reported LGD-to-ECI links,
with separate source dates and ambiguity concerns. Geographic
associations are available in [constituency_coverage](constituency_coverage.md).

Reported LGD-to-ECI mappings are available through the
[urban](constituencies_mapping_urban.md#eci-code-lookup)
and [historical PRI](constituencies_mapping_pri.md#eci-code-lookup) query helpers;
inspect their source dates and ambiguity flags.

## API

```python
from lgd_query.queries import parliament_constituencies

rows = parliament_constituencies.list(db).fetchall()
matches = parliament_constituencies.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `parliament_constituency_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `parliament_constituency_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `parliament_constituency_name` | Supplied `parliament_constituency_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `parliament_constituency_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `parliament_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `parliament_constituency_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query parliament_constituencies list --format json
lgd-query parliament_constituencies search NAME --mode fuzzy --cache-dir ./data
lgd-query parliament_constituencies code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/parliament_constituencies.md) and [shared query rules](../QUERIES.md).
