# org_unit_details

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/org_unit_details.md) · [API/CLI conventions](../QUERIES.md)

This combined report adds office details for state and central
organization units: parent office, organization-specific identifier,
email, telephone, address and a typed location code/name. It is keyed
by `organization_unit_code`; organization and state remain attributes.
State scope `0` denotes central organizations.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

- `by_code(db, code, **filters)` selects `organization_unit_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_unit_name`.

`organization_code` and `state_code` remain optional filters. Name enrichment
of other reports still checks matching state scope as well as unit, organization and location;
this is a consistency check across reports, not an extra field in this key.

## Follow location codes

`entities(db, entity_type=..., **filters)` follows the details report's typed
location references to full register records. Load its inputs with
`entity_sources(release, type_value, observed_on=None)`; inspect them without
metadata using `required_entity_datasets(type_value)`.

This combined report routes custom administrative-unit locations to central
units for state scope `0`, and to state units with the same state scope otherwise.
Pass `state_code` to the dependency helpers as well as the query, or prepare
once. A custom-level query restricted to state scope `0` loads only central
administrative units; a nonzero state loads only state units. Unfiltered queries
load both. Geographic locations are resolved by typed code, independently of organization
scope. The [shared type mapping and result semantics](../ORGANIZATION_QUERIES.md#follow-entity-references-to-registers)
cover local-body type disagreements, unknown types and missing references.

```sh
lgd-query org_unit_details entities --entity-type=-5 --state-code 32 --format json
```

## Reference exploration

`reference_types` (CLI `types`) inspects this report's source types without
loading target registers. `reference_type_map()` lists known namespaces without I/O.
`references` retains source rows and unresolved outcomes alongside matched targets.
See the [organization cookbook](../ORGANIZATION_QUERIES.md) for result columns,
resolution statuses and scoped dependencies.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `organization_unit_name` | Supplied `organization_unit_name` | None |
| `parent_organization_unit_name` | Supplied `parent_organization_unit_name` | None |
| `entity_type_name` | Supplied `entity_type_name` | None |
| `entity_name` | Supplied `entity_name` | None |
| `organization_name` | Supplied `organization_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `organization_unit_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `organization_unit_code`, `parent_organization_unit_code`, `organization_code`, `state_code` |
| Text | `organization_unit_name`, `parent_organization_unit_name`, `organization_unit_specific_code`, `organization_unit_email`, `organization_unit_contact_number`, `organization_unit_address`, `entity_type_name`, `entity_name`, `organization_name`, `state_name` |
| Signed code | `entity_type`, `entity_code` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query org_unit_details list --limit 5
```
