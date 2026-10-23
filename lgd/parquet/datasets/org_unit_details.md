# org_unit_details

One reported organization-unit/organization/state record. Organization-specific codes can contain letters, spaces and leading zeroes. Email, contact number and address are text, including blank and literal zero placeholders. Signed entity_type values encode reported location types (including local-body types); entity_type_name is its supplied label. Parent references can be unresolved within the report. Absence from a subsequent metadata report does not establish deletion.

## Row identity and conversion

The reported record key is:

```text
(organization_unit_code, organization_code, state_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `organization_unit_code` | `VARCHAR` | `Org Unit Code` | No |
| 2 | `organization_unit_name` | `VARCHAR` | `Org Unit Name (In English)` | No |
| 3 | `parent_organization_unit_code` | `VARCHAR` | `Parent Org Unit Code` | No |
| 4 | `parent_organization_unit_name` | `VARCHAR` | `Parent Org Unit Name` | No |
| 5 | `organization_unit_specific_code` | `VARCHAR` | `Org Specific Code` | No |
| 6 | `organization_unit_email` | `VARCHAR` | `Organization Email ID` | No |
| 7 | `organization_unit_contact_number` | `VARCHAR` | `Organization Contact Number` | No |
| 8 | `organization_unit_address` | `VARCHAR` | `Organization Address` | No |
| 9 | `entity_type` | `VARCHAR` | `Entity Type` | No |
| 10 | `entity_type_name` | `VARCHAR` | `Entity Type Name` | No |
| 11 | `entity_code` | `VARCHAR` | `Entity Code` | No |
| 12 | `entity_name` | `VARCHAR` | `Entity Name` | No |
| 13 | `organization_code` | `VARCHAR` | `Base Organization Code` | No |
| 14 | `organization_name` | `VARCHAR` | `Base Organization Name` | No |
| 15 | `state_code` | `VARCHAR` | `State Code` | No |
| 16 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
