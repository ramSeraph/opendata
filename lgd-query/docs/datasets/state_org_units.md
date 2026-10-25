# state_org_units

This directory lists offices/units of state organizations, with
unit names, parent-unit references, organization, state, own level and
typed location codes. `organization_unit_code` identifies a unit;
organization and state remain attributes and filters. Location
describes where the unit is reported, not the places it covers.

[org_unit_details](org_unit_details.md) can supply the missing location
name plus contact/address fields; the query API can include that name
on request. [org_unit_coverage](org_unit_coverage.md) supplies separate
coverage claims. Matching details uses the unit, organization, state
and typed location reference, so a different report's location is
not silently substituted.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

```python
from lgd_query.queries import state_org_units

rows = state_org_units.list(db).fetchall()
matches = state_org_units.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `organization_unit_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_unit_name`.

### Include the location name

`list`, `by_code` and `search` accept `include_entity_name=True`. Load the
additional report through the dependency helper:

```python
from lgd_query import connect, queries

inputs = queries.sources(release, "state_org_units", include_entity_name=True)
with connect(inputs, cache_dir="./data") as db:
    rows = state_org_units.by_code(
        db, 1237173, include_entity_name=True
    ).fetchall()
```

The result keeps every selected unit row and adds `entity_names` (all distinct
nonblank labels, sorted) and `entity_name` (the single label when unambiguous).
Missing references produce `[]` and NULL; conflicting labels produce their
alternatives and NULL. References never multiply unit rows. By default these
columns and the extra dependency are absent. Search matching, limits and fuzzy
ranking are unchanged when location names are included.

The join checks the reported unit, organization, state, entity code and entity
type using the keys below. Unit identity alone does not establish that another
report describes the same location. Inspect input report dates; `observed_on`
applies to both the unit directory and details when explicitly supplied.

Name enrichment also adds `entity_name_status`: `matched`, `missing`, or
`ambiguous`. Use that keyword (CLI `--entity-name-status`) or exact `entity_name`
to filter derived labels; either option automatically enables enrichment.
`is_null="entity_name"` selects missing or ambiguous labels. These filters apply
before search limits. See [name outcomes](../ORGANIZATION_DATA.md#filter-reported-location-name-outcomes).

## Follow location codes

`entities(db, entity_type=..., **filters)` follows the selected offices' location
references to full register records. For example, type `2` resolves districts,
type `4` resolves villages, negative local-body types search the three body
registers, and custom level codes resolve state administrative units by level,
unit and state. Filters such as `organization_unit_code` select office rows.

Load inputs with `entity_sources(release, type_value, observed_on=None)`, or
inspect `required_entity_datasets(type_value)`. This differs from
`include_entity_name=True`: it returns referenced entities instead of enriched
office rows. See the [type mapping and result semantics](../ORGANIZATION_DATA.md#follow-entity-references-to-registers),
including how unmatched references and body-type disagreements are handled.

```sh
lgd-query state_org_units entities --entity-type 2 --organization-unit-code 1237173 --format json
```

## Reference exploration

- `references(db, resolution_status=None, **source_filters)` retains source
  offices/claims, unresolved references and matched register variants. Output
  prefixes distinguish `source_` columns from `target_` columns.
- `reference_types(db, **source_filters)` reads only this report and returns
  observed types/labels, row and distinct-office counts, and known namespaces.
- `reference_type_map()` describes known namespaces without I/O.

Use `queries.prepare("state_org_units", "references", ...)` or
`queries.prepare("state_org_units", "reference_types", ...)` to share options with
input resolution. Optional reference type and report-state filters narrow target
inputs. A missing required register fails explicitly. `entities` rejects unknown
type selections; `references` preserves unknown source references as evidence.

```sh
lgd-query state_org_units types --all
lgd-query state_org_units references --help
```

See [reference outcomes and dependencies](../ORGANIZATION_DATA.md#keep-offices-claims-and-unresolved-references)
and [type discovery](../ORGANIZATION_DATA.md#inspect-types-before-resolving-references).

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

Lookup searches add `lookup_names` containing all distinct resolved labels. Multiple labels do not multiply the source row. Missing references do not match. The matching report can have a different date; inspect `queries.sources(...)` before opening it. Supplied columns remain unchanged.

The level-name lookup matches this unit's own `organization_level_code` to
`org_unit_coverage.report_organization_level_code`, within the same organization
and state/Centre scope. Coverage selections can include descendants: a unit
is **not** assigned the selected level just because it appears in that report.
Only levels present as named selections can resolve this way. The designation
reports are not used for this join: all their level codes are blank in the
23 October 2026 release, despite having level names.

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `organization_unit_code` | Integer or ASCII digit string; zeros preserved |
| `organization_unit_name` | Exact string |
| `organization_unit_name_local` | Exact string |
| `entity_type` | Signed integer or exact integer text |
| `entity_code` | Signed integer or exact integer text |
| `parent_organization_unit_code` | Integer or ASCII digit string; zeros preserved |
| `parent_organization_unit_name` | Exact string |
| `organization_level_code` | Integer or ASCII digit string; zeros preserved |
| `organization_code` | Integer or ASCII digit string; zeros preserved |
| `organization_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query state_org_units list --format json
lgd-query state_org_units search NAME --mode fuzzy --cache-dir ./data
lgd-query state_org_units code CODE --help
lgd-query state_org_units code 1237173 --include-entity-name --format json
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/state_org_units.md) and [shared query rules](../QUERIES.md).
