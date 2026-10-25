# org_unit_coverage

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/org_unit_coverage.md) · [API/CLI conventions](../QUERIES.md)

This combined state/central report describes the places organization
units are reported to cover. Each row is either a geographic claim
or an explicit record that coverage details were not supplied.
`covered_entity_*` describes the target; `entity_code` and `entity_name`
describe the office's location reference. The location's type is not supplied
here. State scope `0` denotes central organizations.

The key is `(organization_unit_code, covered_entity_type, covered_entity_code)`.
Other fields are attributes. Exact duplicate rows collapse; conflicting attributes
for one key reject conversion. No-details rows use blank target type/code and do
not mean zero coverage. Missing target types remain unresolved.

Report-selection levels may return descendant offices and are not each office's
own level. See the linked schema for field definitions and missing-details
behavior. Inspect the selected release's source date before combining reports.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

- `list(db, **filters)` returns matching normalized associations and no-details rows.
- `by_code(db, code, **filters)` selects `organization_unit_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_unit_name`.

## Follow covered-entity codes

`entities(db, covered_entity_type=..., **filters)` returns full register records
for targets of matching claims. It follows `covered_entity_code`, not the
office-location `entity_code`. Only claims with
`coverage_details_reported='true'` select targets. Other filters, including
`organization_unit_code`, `state_code` and `coverage_type`, select source claims.

Load inputs with `entity_sources(release, type_label, observed_on=None)`; inspect
them using `required_entity_datasets(type_label)`. Type labels use exact source
spelling, such as `Subdistrict`, `Village` or `Village Panchayat`. Blank and
unrecognized type selections fail validation in `entities`; use `references`
to retain the source claims and their unresolved outcomes. See the
[shared type mapping and result semantics](../ORGANIZATION_QUERIES.md#follow-entity-references-to-registers).

```sh
lgd-query org_unit_coverage entities --covered-entity-type Village --coverage-type F --format json
```

Repeated claims do not multiply returned entity records. Register variants
remain separate; local-body subtype disagreements are exposed through
`reference_type_matches`. Ordinary `list`/`by_code` include normalized claims that cannot be resolved,
including missing target types.

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
| `entity_name` | Supplied `entity_name` | None |
| `covered_entity_name` | Supplied `covered_entity_name` | None |
| `report_organization_level_name` | Supplied `report_organization_level_name` | None |
| `organization_name` | Supplied `organization_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `organization_unit_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `organization_unit_code`, `covered_entity_code`, `report_organization_level_code`, `organization_code`, `state_code` |
| Text | `organization_unit_name`, `entity_name`, `organization_unit_specific_code`, `covered_entity_name`, `covered_entity_type`, `coverage_type`, `coverage_details_reported`, `report_organization_level_name`, `organization_name`, `state_name` |
| Signed code | `entity_code` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query org_unit_coverage list --limit 5
```

A blank covered-entity type is unresolved. Search never guesses its namespace or reconstructs an absent coverage claim. The unit location and coverage targets remain distinct.
