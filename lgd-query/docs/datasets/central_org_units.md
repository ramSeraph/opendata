# central_org_units

This directory lists offices/units of central organizations, with
unit names, parent-unit references, organization, own level and typed
location codes. `organization_unit_code` identifies a unit;
organization is an attribute. There are no state columns, even when
offices are located in individual states.

[org_unit_details](org_unit_details.md) supplies optional location
names and contact/address fields; [org_unit_coverage](org_unit_coverage.md)
supplies separate geographic claims. Both combined reports use state
scope `0` for central organizations. The optional location-name lookup
matches unit, organization and typed location within that scope.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

```python
from lgd_query.queries import central_org_units

rows = central_org_units.list(db).fetchall()
matches = central_org_units.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `organization_unit_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_unit_name`.

### Include the location name

`list`, `by_code` and `search` accept `include_entity_name=True`. The dependency
helper then loads `org_unit_details` alongside the unit directory:

```python
from lgd_query import connect, queries

inputs = queries.sources(release, "central_org_units", include_entity_name=True)
with connect(inputs, cache_dir="./data") as db:
    rows = central_org_units.list(db, include_entity_name=True).fetchall()
```

The result adds `entity_names`, a sorted array of distinct nonblank labels,
and `entity_name`, populated only for one unambiguous match. Missing references
produce `[]` and NULL. Conflicting labels remain alternatives with a NULL scalar.
Every selected unit row is retained; references do not multiply rows. Defaults
do not add these columns or load the details report. Search limits and ranking
are preserved.

The join checks unit, organization and the typed entity reference and restricts
details to the central scope (`state_code='0'`). Inspect input dates; an explicit
`observed_on` guard applies to both reports.

## Follow location codes

`entities(db, entity_type=..., **filters)` follows the selected offices' location
references to full register records. Type `2` resolves districts, for example;
custom levels such as `1254` resolve central administrative units using both
the level and unit codes. Central report scope does not restrict geographic
matches to a state numbered zero. International type `-100` remains unresolved.

Load inputs with `entity_sources(release, type_value, observed_on=None)`, or
inspect `required_entity_datasets(type_value)`. This returns entity records;
`include_entity_name=True` separately enriches office rows with details-report
labels. See the [type mapping and result semantics](../ORGANIZATION_DATA.md#follow-entity-references-to-registers).

```sh
lgd-query central_org_units entities --entity-type 1254 --format json
```

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `organization_unit_name` | Supplied `organization_unit_name` | None |
| `organization_unit_name_local` | Supplied `organization_unit_name_local` | None |
| `parent_organization_unit_name` | Supplied `parent_organization_unit_name` | None |
| `organization_name` | Supplied `organization_name` | None |
| `english` | Supplied `organization_unit_name` | None |
| `local` | Supplied `organization_unit_name_local` | None |
| `entity_name` | `org_unit_details.entity_name` | `org_unit_details` |
| `organization_level_name` | `org_unit_coverage.report_organization_level_name` | `org_unit_coverage` |

Lookup keys are explicit and names never serve as join keys:

- `entity_name`: `organization_unit_code` → `org_unit_details.organization_unit_code`, `organization_code` → `org_unit_details.organization_code`, `entity_code` → `org_unit_details.entity_code`, `entity_type` → `org_unit_details.entity_type`. Restrict lookup `state_code` to `0`.
- `organization_level_name`: `organization_level_code` → `org_unit_coverage.report_organization_level_code`, `organization_code` → `org_unit_coverage.organization_code`. Restrict lookup `state_code` to `0`.

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

## CLI

```sh
lgd-query central_org_units list --format json
lgd-query central_org_units search NAME --mode fuzzy --cache-dir ./data
lgd-query central_org_units code CODE --help
lgd-query central_org_units list --include-entity-name --format json
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/central_org_units.md) and [shared query rules](../QUERIES.md).
