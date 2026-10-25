# org_unit_coverage

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

```python
from lgd_query.queries import org_unit_coverage

rows = org_unit_coverage.list(db).fetchall()
matches = org_unit_coverage.search(db, "name", mode="contains").fetchall()
```

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
[shared type mapping and result semantics](../ORGANIZATION_DATA.md#follow-entity-references-to-registers).

```sh
lgd-query org_unit_coverage entities --covered-entity-type Village --coverage-type F --format json
```

Repeated claims do not multiply returned entity records. Register variants
remain separate; local-body subtype disagreements are exposed through
`reference_type_matches`. Ordinary `list`/`by_code` include normalized claims that cannot be resolved,
including missing target types.

## Reference exploration

- `references(db, resolution_status=None, **source_filters)` retains source
  offices/claims, unresolved references and matched register variants. Output
  prefixes distinguish `source_` columns from `target_` columns.
- `reference_types(db, **source_filters)` reads only this report and returns
  observed types/labels, row and distinct-office counts, and known namespaces.
- `reference_type_map()` describes known namespaces without I/O.

Use `queries.prepare("org_unit_coverage", "references", ...)` or
`queries.prepare("org_unit_coverage", "reference_types", ...)` to share options with
input resolution. Optional reference type and report-state filters narrow target
inputs. A missing required register fails explicitly. `entities` rejects unknown
type selections; `references` preserves unknown source references as evidence.

```sh
lgd-query org_unit_coverage types --all
lgd-query org_unit_coverage references --help
```

See [reference outcomes and dependencies](../ORGANIZATION_DATA.md#keep-offices-claims-and-unresolved-references)
and [type discovery](../ORGANIZATION_DATA.md#inspect-types-before-resolving-references).

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

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `organization_unit_code` | Integer or ASCII digit string; zeros preserved |
| `organization_unit_name` | Exact string |
| `entity_code` | Signed integer or signed ASCII digit string; sentinels preserved |
| `entity_name` | Exact string |
| `organization_unit_specific_code` | Exact string |
| `covered_entity_code` | Integer or ASCII digit string; zeros preserved |
| `covered_entity_name` | Exact string |
| `covered_entity_type` | Exact string |
| `coverage_type` | Exact string |
| `coverage_details_reported` | Exact string |
| `report_organization_level_code` | Integer or ASCII digit string; zeros preserved |
| `report_organization_level_name` | Exact string |
| `organization_code` | Integer or ASCII digit string; zeros preserved |
| `organization_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query org_unit_coverage list --format json
lgd-query org_unit_coverage search NAME --mode fuzzy --cache-dir ./data
lgd-query org_unit_coverage code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

A blank covered-entity type is unresolved. Search never guesses its namespace or reconstructs an absent coverage claim. The unit location and coverage targets remain distinct.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/org_unit_coverage.md) and [shared query rules](../QUERIES.md).
