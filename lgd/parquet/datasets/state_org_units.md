# state_org_units

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/state_org_units.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

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
This includes simultaneous disagreement about organization or state. The
historical key review
found no such conflicts across all 1,346 accepted observations.

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
| 11 | `state_code` | `VARCHAR` | `State Code` | No |
| 12 | `state_name` | `VARCHAR` | `State Name` | No |
