# state_orgs

This directory identifies state departments and organizations by
`organization_code`, with names, organization type, state and reported
parent organization. State is an attribute. The parent may appear
only as a reference, so the directory need not contain a row for every
parent in the hierarchy.

Offices belonging to these organizations are reported separately in
[state_org_units](state_org_units.md). Administrative level definitions
in [state_admin_depts](state_admin_depts.md) describe a different
concept despite that dataset's filename.

## Row identity and conversion

Type labels and blank parent codes remain as supplied.

The reported record key is:

```text
(organization_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.
Simultaneous disagreement about state is also a conflict. The
historical review
found no code shared across states in the accepted history.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `organization_code` | `VARCHAR` | `Organization Code` | No |
| 2 | `organization_name` | `VARCHAR` | `Organization Name` | No |
| 3 | `organization_type` | `VARCHAR` | `Organization Type` | No |
| 4 | `parent_organization_code` | `VARCHAR` | `Parent Organization Code` | No |
| 5 | `parent_organization_name` | `VARCHAR` | `Parent Organization Name` | No |
| 6 | `parent_organization_type` | `VARCHAR` | `Parent Organization Type` | No |
| 7 | `state_code` | `VARCHAR` | `State Code` | No |
| 8 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
