# org_unit_details

This combined report adds office details for state and central
organization units: parent office, organization-specific identifier,
email, telephone, address and a typed location code/name. It is keyed
by `organization_unit_code`; organization and state remain attributes.
State scope `0` denotes central organizations.

It enriches [state_org_units](state_org_units.md) and
[central_org_units](central_org_units.md), including the location
`entity_name` that their directories omit. A location is separate
from geographic coverage in [org_unit_coverage](org_unit_coverage.md).
Details can be missing or incomplete; absence from this report does
not establish that the office no longer exists.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

```python
from lgd_query.queries import org_unit_details

rows = org_unit_details.list(db).fetchall()
matches = org_unit_details.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, value, **filters)` selects `organization_unit_code` exactly and retains all matches.
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
Geographic locations are resolved by typed code, independently of organization
scope. The [shared type mapping and result semantics](../ORGANIZATION_DATA.md#follow-entity-references-to-registers)
cover local-body type disagreements, unknown types and missing references.

```sh
lgd-query org_unit_details entities --entity-type=-5 --state-code 32 --format json
```

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

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `organization_unit_code` | Integer or ASCII digit string; zeros preserved |
| `organization_unit_name` | Exact string |
| `parent_organization_unit_code` | Integer or ASCII digit string; zeros preserved |
| `parent_organization_unit_name` | Exact string |
| `organization_unit_specific_code` | Exact string |
| `organization_unit_email` | Exact string |
| `organization_unit_contact_number` | Exact string |
| `organization_unit_address` | Exact string |
| `entity_type` | Signed integer or exact integer text |
| `entity_type_name` | Exact string |
| `entity_code` | Signed integer or exact integer text |
| `entity_name` | Exact string |
| `organization_code` | Integer or ASCII digit string; zeros preserved |
| `organization_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |
| `state_name` | Exact string |

## CLI

```sh
lgd-query org_unit_details list --format json
lgd-query org_unit_details search NAME --mode fuzzy --cache-dir ./data
lgd-query org_unit_details code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/org_unit_details.md) and [shared query rules](../QUERIES.md).
