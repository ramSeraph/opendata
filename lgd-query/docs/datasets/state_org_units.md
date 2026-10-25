# state_org_units

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/state_org_units.md) · [API/CLI conventions](../QUERIES.md)

This directory lists offices/units of state organizations, with
unit names, parent-unit references, organization, state, own level and
typed location codes. `organization_unit_code` identifies a unit;
organization and state remain attributes and filters. Location
describes where the unit is reported, not the places it covers.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

- `by_code(db, code, **filters)` selects `organization_unit_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_unit_name`.

### Include the location name

`include_entity_name=True` adds details-report labels without multiplying office
rows. `entity_name` is NULL unless unique; `entity_names` preserves alternatives.
Filter with `entity_name` or `entity_name_status` (`matched`, `missing`, `ambiguous`)
to enable enrichment automatically. See [name outcomes](../ORGANIZATION_QUERIES.md#filter-reported-location-name-outcomes).

## Follow location codes

`entities(entity_type=...)` returns matched register records; `references`
retains source offices and unresolved outcomes. `reference_types` (CLI `types`)
counts observed types without loading target registers; `reference_type_map()`
lists known namespaces without I/O. Custom location levels resolve against state administrative units.
See the [organization cookbook](../ORGANIZATION_QUERIES.md) for type codes,
dependencies and result columns.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `organization_unit_name` | Supplied `organization_unit_name` | None |
| `organization_unit_name_local` | Supplied `organization_unit_name_local` | None |
| `parent_organization_unit_name` | Supplied `parent_organization_unit_name` | None |
| `organization_name` | Supplied `organization_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `organization_unit_name` | None |
| `local` | Supplied `organization_unit_name_local` | None |
| `entity_name` | `org_unit_details.entity_name` | `org_unit_details` |
| `organization_level_name` | `org_unit_coverage.report_organization_level_name` | `org_unit_coverage` |

Lookup keys are explicit and names never serve as join keys:

- `entity_name`: `organization_unit_code` → `org_unit_details.organization_unit_code`, `organization_code` → `org_unit_details.organization_code`, `state_code` → `org_unit_details.state_code`, `entity_code` → `org_unit_details.entity_code`, `entity_type` → `org_unit_details.entity_type`.
- `organization_level_name`: `organization_level_code` → `org_unit_coverage.report_organization_level_code`, `organization_code` → `org_unit_coverage.organization_code`, `state_code` → `org_unit_coverage.state_code`.

Level names resolve only from selections matching the office’s own level, not
from a parent-level selection that happens to include it. See
[name lookup rules](../ORGANIZATION_QUERIES.md#where-the-apis-get-missing-names).

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `organization_unit_code`, `parent_organization_unit_code`, `organization_level_code`, `organization_code`, `state_code` |
| Text | `organization_unit_name`, `organization_unit_name_local`, `parent_organization_unit_name`, `organization_name`, `state_name` |
| Signed code | `entity_type`, `entity_code` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query state_org_units code 1237173 --include-entity-name --format json
```
