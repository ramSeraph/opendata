# assembly_constituencies

LGD's assembly-constituency register supplies an assembly's code
and name together with parliamentary-constituency and state references.
`assembly_constituency_code` identifies the row; the parliamentary
parent and state are attributes. Parliamentary-only placeholders
with no assembly code or name are omitted.

These are LGD identifiers. ECI numbers are supplied separately in the
PRI and urban constituency-mapping reports, where some reported
mappings are ambiguous. Use [constituency_coverage](constituency_coverage.md)
for links from geographic entities to constituencies.

Reported LGD-to-ECI mappings are available through the
[urban](constituencies_mapping_urban.md#eci-code-lookup)
and [historical PRI](constituencies_mapping_pri.md#eci-code-lookup) query helpers;
inspect their source dates and ambiguity flags.

## API

```python
from lgd_query.queries import assembly_constituencies

rows = assembly_constituencies.list(db).fetchall()
matches = assembly_constituencies.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `assembly_constituency_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `assembly_constituency_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `assembly_constituency_name` | Supplied `assembly_constituency_name` | None |
| `parliament_constituency_name` | Supplied `parliament_constituency_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `assembly_constituency_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `assembly_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `assembly_constituency_name` | Exact string |
| `parliament_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `parliament_constituency_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query assembly_constituencies list --format json
lgd-query assembly_constituencies search NAME --mode fuzzy --cache-dir ./data
lgd-query assembly_constituencies code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/assembly_constituencies.md) and [shared query rules](../QUERIES.md).
