# state_org_designations

This report lists designation titles within state organizations,
with English/local names and reported organization-level associations.
It describes posts or roles, not the people holding them or a staffing
assignment to a particular office.

One designation can be associated with several levels. Level codes
may be blank, and distinct level names are retained in record
identity. Organization and state provide context; join
[state_orgs](state_orgs.md) by organization code to inspect the parent
organization rather than matching a designation's name to an office.

## Row identity and conversion

Distinct reported level names remain separate even for the same level
code. Local-language names remain text.

The normalized record key is:

```text
(designation_code, organization_level_code, organization_level_name)
```

Organization code/name and state code/name remain attributes.
The retained-history review
finds no simultaneous collisions under this key. Using only designation and
level codes would collide for 235 designation codes in the retained history.
Distinct names for the same level code remain separate associations; a scope change for the same
three-field key updates its attributes.

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `designation_code` | `VARCHAR` | `Designation Code` | No |
| 2 | `designation_name` | `VARCHAR` | `Designation Name (In English)` | No |
| 3 | `designation_name_local` | `VARCHAR` | `Designation Name Local (In Local)` | No |
| 4 | `organization_level_code` | `VARCHAR` | `Org Located Level Code` | No |
| 5 | `organization_level_name` | `VARCHAR` | `Org Level Specific Name` | No |
| 6 | `organization_code` | `VARCHAR` | `Base Organization Code` | No |
| 7 | `organization_name` | `VARCHAR` | `Base Organization Name` | No |
| 8 | `state_code` | `VARCHAR` | `State Code` | No |
| 9 | `state_name` | `VARCHAR` | `State Name` | No |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
