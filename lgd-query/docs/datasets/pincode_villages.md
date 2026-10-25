# pincode_villages

LGD's village/pincode report supplies village and postal-code
associations with state, district and subdistrict codes/names. The
normalized key is `(village_code, pincode)`; administrative parents
are attributes. Several pincodes can be associated with one village.

Use `village_code` to connect to [villages](villages.md). A pincode is
a postal identifier stored as text, not an LGD entity code. The report
records LGD's postal links; it does not establish delivery boundaries
or a one-to-one village/postal-area relationship.

## API

```python
from lgd_query.queries import pincode_villages

rows = pincode_villages.list(db).fetchall()
matches = pincode_villages.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
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
| `pincode` | Exact string |
| `subdistrict_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_name` | Exact string |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query pincode_villages list --format json
lgd-query pincode_villages search NAME --mode fuzzy --cache-dir ./data
lgd-query pincode_villages code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/pincode_villages.md) and [shared query rules](../QUERIES.md).
