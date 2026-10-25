# constituency_coverage

This report links typed geographic entities to parliamentary or
assembly constituencies. `entity_type` is District, SubDistrict,
Village, Localbody or Ward; it determines which register an
`entity_code` refers to. A supplied assembly code identifies an
assembly link; otherwise the row is a parliamentary-only link.

Full/partial coverage is an attribute of the association. When both
values are reported for the same association, normalized
`coverage_type` is NULL and the original claims remain recoverable.
Reports known to omit alternative links are incomplete: standalone
Parquet contains supplied associations, while history can retain
older alternatives as not updated. These flags do not quantify
population or identify individual covered children.

The conversion receipt links the original contradictory claims as discrepancy
evidence. Older published generations may still contain separate
Full/Partial rows; the helpers do not silently normalize them on read.

## API

```python
from lgd_query.queries import constituency_coverage

rows = constituency_coverage.list(db).fetchall()
matches = constituency_coverage.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching published row.
- `by_code(db, code, **filters)` selects `entity_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `entity_name`.

`entity_type` is required whenever filtering or looking up `entity_code`; numeric codes alone do not identify the namespace.

## Follow entity codes to their registers

`entities(db, *, entity_type, **filters)` returns the full register records
referenced by matching coverage claims. `entity_type` is required and uses the
exact source spellings below. Joins use LGD entity code and state code; names
are never join keys.

| `entity_type` | Reference datasets | Code column |
| --- | --- | --- |
| `District` | [`districts`](districts.md) | `district_code` |
| `SubDistrict` | [`subdistricts`](subdistricts.md) | `subdistrict_code` |
| `Village` | [`villages`](villages.md) | `village_code` |
| `Localbody` | [`urban_local_bodies`](urban_local_bodies.md), [`pri_local_bodies`](pri_local_bodies.md), [`traditional_local_bodies`](traditional_local_bodies.md) | `local_body_code` |
| `Ward` | [`urban_local_body_wards`](urban_local_body_wards.md), [`pri_local_body_wards`](pri_local_body_wards.md) | `ward_code` |

```python
from lgd_query import load_release, connect
from lgd_query.queries import constituency_coverage

release = load_release()
inputs = constituency_coverage.entity_sources(release, "SubDistrict")
print([(source.name, source.observed_on) for source in inputs])
with connect(inputs, cache_dir="./data") as db:
    # The reference row includes Sidhaw's district and other register fields.
    entity = constituency_coverage.entities(
        db, entity_type="SubDistrict", entity_code="1013"
    ).fetchall()
    # Inspect the associations, including unresolved coverage attributes.
    claims = constituency_coverage.by_code(
        db, "1013", entity_type="SubDistrict"
    ).fetchall()
```

`required_entity_datasets(entity_type)` lists the necessary views without
reading metadata. `entity_sources(release, entity_type, observed_on=None)`
resolves them from one pinned release; the optional date guard applies to all
inputs. Only the selected type's registers are loaded. Missing/unavailable
registers fail explicitly before files are downloaded.

The result starts with `entity_dataset`, `entity_type`, `entity_code` and
`entity_name`, followed by every reference column. Here `entity_name` is the
register's label; the original claim's label remains in `list`/`by_code`.
Several registers use a union by column name, with NULL for columns absent
from a register. `entity_dataset` identifies the source of each row.

Filters apply to the **coverage report**, including constituency codes and
coverage type. Further filter the returned relation by register attributes:

```python
inputs = constituency_coverage.entity_sources(release, "Village")
with connect(inputs, cache_dir="./data") as db:
    villages = constituency_coverage.entities(
        db, entity_type="Village", assembly_constituency_code="1349"
    ).filter("subdistrict_code = '1013'").fetchall()
```

Repeated coverage claims do not multiply reference rows. Multiple matching
register rows remain visible, including village categories and genuine source
duplicates. This helper makes no choice between conflicting Full/Partial
coverage flags. An unresolved claim returns no reference row; it remains
available through `list` and `by_code`. Code `0` and blank codes do not resolve.
Reference datasets may have different observation dates; a match does not prove
that the claimed relationship or coverage was valid on another date.

Select unresolved normalized flags using the returned DuckDB relation:

```python
conflicts = constituency_coverage.list(db).filter("coverage_type IS NULL")
```

`coverage_type=None` leaves the helper filter unused; it is not an SQL NULL
predicate. For a normalized NULL, the distinct reported values are exactly
`Fully Covered` and `Partly Covered`. Other conflicting attributes are rejected
by conversion. Resolving flags against another report requires its own dated
evidence; this API does not infer a correction.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `entity_name` | Supplied `entity_name` | None |
| `parliament_constituency_name` | Supplied `parliament_constituency_name` | None |
| `assembly_constituency_name` | Supplied `assembly_constituency_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `entity_name` | None |

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `constituency_level` | Exact `assembly` or `parliament` |
| `constituency_code` | LGD code in that level; filter level as well |
| `entity_code` | Integer or ASCII digit string; zeros preserved |
| `entity_name` | Exact string |
| `entity_type` | Exact string |
| `parliament_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `parliament_constituency_name` | Exact string |
| `assembly_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `assembly_constituency_name` | Exact string |
| `coverage_type` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query constituency_coverage list --format json
lgd-query constituency_coverage search NAME --mode fuzzy --cache-dir ./data
lgd-query constituency_coverage code CODE --help
lgd-query constituency_coverage entities --entity-type SubDistrict --entity-code 1013 --format json
lgd-query constituency_coverage entities --entity-type Village --assembly-constituency-code 1349
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/constituency_coverage.md) and [shared query rules](../QUERIES.md).
