# traditional_local_bodies

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/traditional_local_bodies.md) · [API/CLI conventions](../QUERIES.md)

This register describes traditional local bodies, their state and
reported district/intermediate parent paths. The institutions and
names vary by state. `local_body_level` gives District, Intermediate
or Village; `local_body_type_code` and `local_body_type_name`, when
supplied, describe the kind of body. Older reports supply types that newer layouts may omit.

`local_body_code` identifies the body. The row key additionally includes
`district_panchayat_code` and `intermediate_panchayat_code` because historical
reports can assert more than one parent path for the same body. Count distinct
body codes for bodies; count rows for reported paths. See the
[state hierarchy, historical names and source oddities](../../../lgd/parquet/datasets/traditional_local_bodies.md#state-wise-levels-and-names).

## API

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

| Value type | Filters |
| --- | --- |
| Code | `local_body_code`, `local_body_type_code`, `district_panchayat_code`, `intermediate_panchayat_code`, `state_code` |
| Integer | `local_body_version` |
| Text | `local_body_name`, `local_body_name_local`, `local_body_type_name`, `state_name`, `local_body_level` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query traditional_local_bodies search Unakoti --field district_panchayat_name --state-code 16
lgd-query traditional_local_bodies search Ambassa --field intermediate_panchayat_name --state-code 16
```

Parent-name searches automatically load both body registers. Listing and
body-code lookups need only `traditional_local_bodies`.
