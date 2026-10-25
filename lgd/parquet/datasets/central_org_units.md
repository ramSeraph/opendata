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

See the [entity type reference](org_unit_details.md#entity-type-reference)
for every observed signed `entity_type` value <= 5, its supplied label,
and the blank-label cases. These labels were checked in `org_unit_details`.

## Row identity and conversion

Entity codes can be signed source sentinels; blank parent and level codes
remain blank. Parent-unit and location references are reported values,
not verified foreign keys.

The reported record key is:

```text
(organization_unit_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.
This includes simultaneous disagreement about organization. The
historical key review
found no such conflicts across all 1,610 accepted observations.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `organization_unit_code` | `VARCHAR` | `Org Unit Code` | No |
| 2 | `organization_unit_name` | `VARCHAR` | `Org Unit Name (In English)` | No |
| 3 | `organization_unit_name_local` | `VARCHAR` | `Org Unit Name (In Local)` | No |
| 4 | `entity_type` | `VARCHAR` | `Entity Type` | No |
| 5 | `entity_code` | `VARCHAR` | `Entity Lc` | No |
| 6 | `parent_organization_unit_code` | `VARCHAR` | `Parent Org Unit Code` | No |
| 7 | `parent_organization_unit_name` | `VARCHAR` | `Parent Org Unit Name` | No |
| 8 | `organization_level_code` | `VARCHAR` | `Org Located Level Code` | No |
| 9 | `organization_code` | `VARCHAR` | `Base Organization Code` | No |
| 10 | `organization_name` | `VARCHAR` | `Base Organization Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
