# traditional_local_bodies

This register describes traditional local bodies, their state and
reported district/intermediate parent paths. The institutions and
names vary by state. `local_body_level` gives District, Intermediate
or Village; `local_body_type_code` and `local_body_type_name`, when
supplied, describe the kind of body. Older reports supply types that newer layouts may omit.

A body can have several reported parent paths. Parent resolution needs
both this register and [pri_local_bodies](pri_local_bodies.md). In the
reviewed 23 October 2026 snapshot, some Tripura rows reference PRI parents,
while Meghalaya lists village-level bodies and district councils without
linking their parent codes.
Preserve those unresolved relationships; a successful name lookup
alone does not verify the hierarchy.

`local_body_code` identifies the body. The row key additionally includes
`district_panchayat_code` and `intermediate_panchayat_code` because historical
reports can assert more than one parent path for the same body. Count distinct
body codes for bodies; count rows for reported paths. See the
[state hierarchy, historical names and source oddities](../../../lgd/parquet/datasets/traditional_local_bodies.md#state-wise-levels-and-names).

## API

```python
from lgd_query.queries import traditional_local_bodies

rows = traditional_local_bodies.list(db).fetchall()
matches = traditional_local_bodies.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_name_local` | Supplied `local_body_name_local` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |
| `local` | Supplied `local_body_name_local` | None |
| `district_panchayat_name` | `local_body_name` from both `traditional_local_bodies` and `pri_local_bodies` | `pri_local_bodies` |
| `intermediate_panchayat_name` | `local_body_name` from both `traditional_local_bodies` and `pri_local_bodies` | `pri_local_bodies` |

Lookup keys are explicit and names never serve as join keys:

- `district_panchayat_name`: `district_panchayat_code` → `local_body_code`, within the same `state_code`, in **both** body registers.
- `intermediate_panchayat_name`: `intermediate_panchayat_code` → `local_body_code`, within the same `state_code`, in **both** body registers.

The `panchayat` field names do not restrict the reference to a PRI body. Tripura
has both TLB-to-TLB and TLB-to-PRI assertions. Resolving a name does not validate
the asserted hierarchy. Zero, blank and missing parent references do not match.

Lookup searches add `lookup_names` containing all distinct resolved labels from
both registers, with no preferred source. Multiple labels do not multiply the
source row. The matching report can have a different date; inspect
`queries.sources(...)` before opening it, or require the same date explicitly.
Supplied columns and parent codes remain unchanged.

```python
from lgd_query import connect, load_release, queries

release = load_release()
inputs = queries.sources(release, "traditional_local_bodies", field="district_panchayat_name")
print([(source.name, source.observed_on) for source in inputs])
with connect(inputs, cache_dir="./data") as db:
    rows = traditional_local_bodies.search(
        db, "Unakoti", field="district_panchayat_name", state_code="16"
    ).fetchall()
```

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_version` | Nonnegative integer |
| `local_body_name` | Exact string |
| `local_body_name_local` | Exact string |
| `local_body_type_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_type_name` | Exact string |
| `district_panchayat_code` | Integer or ASCII digit string; zeros preserved |
| `intermediate_panchayat_code` | Integer or ASCII digit string; zeros preserved |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |
| `local_body_level` | Exact string |

## CLI

```sh
lgd-query traditional_local_bodies list --format json
lgd-query traditional_local_bodies search NAME --mode fuzzy --cache-dir ./data
lgd-query traditional_local_bodies code CODE --help
lgd-query traditional_local_bodies search Unakoti --field district_panchayat_name --state-code 16
lgd-query traditional_local_bodies search Ambassa --field intermediate_panchayat_name --state-code 16
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.
Parent-name searches automatically load both body registers. Listing and
body-code lookups need only `traditional_local_bodies`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/traditional_local_bodies.md) and [shared query rules](../QUERIES.md).
