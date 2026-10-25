# nofn_panchayats

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/nofn_panchayats.md) · [API/CLI conventions](../QUERIES.md)

This retired report lists panchayats/local bodies in the National
Optical Fibre Network (NOFN) project, with body codes/names, state and
named district/subdistrict paths. It includes reported PRI and
traditional bodies. One body can have several named paths; district
and subdistrict codes are not supplied.

Collection of this report will not resume in this project. The query helpers
remain available for retained historical Parquet files; a new daily report is
not expected. The CLI requires a release index that actually publishes such a
file, so these commands are not available through the current daily release.

## API

- `by_code(db, code, **filters)` selects `local_body_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `local_body_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `local_body_name` | Supplied `local_body_name` | None |
| `district_name` | Supplied `district_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `local_body_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `local_body_code`, `state_code` |
| Text | `local_body_name`, `district_name`, `subdistrict_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query nofn_panchayats list --limit 5
```
