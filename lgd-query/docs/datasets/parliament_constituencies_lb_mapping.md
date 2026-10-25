# parliament_constituencies_lb_mapping

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/parliament_constituencies_lb_mapping.md) · [API/CLI conventions](../QUERIES.md)

This report links parliamentary constituencies to named
assembly constituencies and local bodies, with a body-type name,
state and coverage flag. The parliamentary reference is coded; assembly
and local-body references are names. Those names identify reported
associations here and cannot safely be converted to unique LGD codes
from spelling alone.

The normalized key is `(parliament_constituency_code, assembly_constituency_name,
local_body_name, local_body_type_name)`. Exact `coverage_type='F'` or `'P'`
filters exclude unresolved associations; use SQL `coverage_type IS NULL`
to select them, or `coverage_type = ''` for literal blank coverage.

## API

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

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `parliament_constituency_code`, `state_code` |
| Text | `parliament_constituency_name`, `assembly_constituency_name`, `local_body_name`, `local_body_type_name`, `coverage_type` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query parliament_constituencies_lb_mapping list --limit 5
```
