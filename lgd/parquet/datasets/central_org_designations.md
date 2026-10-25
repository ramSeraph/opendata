# central_org_designations

This report lists designation titles within central organizations,
including English/local names and reported levels, such as postal
roles at different office levels. It describes titles rather than
named office-holders or individual office staffing.

A designation can occur at several levels; level names remain part
of the association's identity, including when level codes are blank.
There are no state columns. Organization references connect to
[central_orgs](central_orgs.md), while office membership is reported
separately in [central_org_units](central_org_units.md).

## Row identity and conversion

Distinct reported level names remain separate even for the same level
code. Local-language names remain text.

The normalized record key is:

```text
(designation_code, organization_level_code, organization_level_name)
```

Organization code/name remain attributes.
The retained-history review
finds no simultaneous collisions under this key. Using only designation and
level codes would collide for 63 designation codes in the retained history.
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

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
