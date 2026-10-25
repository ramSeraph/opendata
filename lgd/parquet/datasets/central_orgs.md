# central_orgs

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/central_orgs.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This directory identifies central departments and organizations by
`organization_code`, with names, types and reported parent
organizations. It has no state columns. A parent ministry or
organization can appear only as a reference; conversion does not
synthesize a missing parent row.

[central_org_units](central_org_units.md) supplies their offices/units,
while [central_org_designations](central_org_designations.md) supplies
titles and levels. Parent references describe the hierarchy asserted
in the report and are not guaranteed to resolve within the directory.

## Row identity and conversion

Type labels and blank parent codes remain as supplied; no state identifiers are synthesized.

The reported record key is:

```text
(organization_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `organization_code` | `VARCHAR` | `Organization Code` | No |
| 2 | `organization_name` | `VARCHAR` | `Organization Name` | No |
| 3 | `organization_type` | `VARCHAR` | `Organization Type` | No |
| 4 | `parent_organization_code` | `VARCHAR` | `Parent Organization Code` | No |
| 5 | `parent_organization_name` | `VARCHAR` | `Parent Organization Name` | No |
| 6 | `parent_organization_type` | `VARCHAR` | `Parent Organization Type` | No |
