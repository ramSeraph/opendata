# pincode_urban

LGD's urban-body/pincode report supplies local-body and postal-code
associations with body and state names/codes. A body may have several
pincodes. The record key is `(local_body_code, pincode)`; state code/name
remain attributes and filters.

Body codes usually connect to [urban_local_bodies](urban_local_bodies.md).
Historical reports also contain rural/traditional bodies, which can require
the [PRI](pri_local_bodies.md) or [traditional-body](traditional_local_bodies.md)
registers; the dataset name does not restrict its contents to urban bodies.
Pincodes remain text and identify postal references rather than LGD
entities. These links do not supply ward-level addresses or postal
delivery boundaries.

## API

```python
from lgd_query.queries import pincode_urban

rows = pincode_urban.list(db).fetchall()
matches = pincode_urban.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `local_body_type_name` | Exact string |
| `pincode` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query pincode_urban list --format json
lgd-query pincode_urban search NAME --mode fuzzy --cache-dir ./data
lgd-query pincode_urban code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/pincode_urban.md) and [shared query rules](../QUERIES.md).
