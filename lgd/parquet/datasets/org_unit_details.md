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

## Row identity and conversion

Organization-specific codes can contain letters, spaces and leading zeroes.
Email, contact number and address remain text, including blank and
literal zero placeholders. Signed `entity_type` values encode location
types, including local-body types; `entity_type_name` retains the
supplied label. Parent references may be unresolved within the report.

The normalized record key is:

```text
organization_unit_code
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

`organization_code`/`organization_name` and `state_code`/`state_name` remain
attributes. Both observations of 23–24 October 2026 contain 592,639 unique unit
codes; none spans multiple organizations or states. A later organization or state
change updates the same unit record. Conflicting simultaneous values for one
unit code fail conversion.

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

## Entity type reference

`entity_type` identifies the kind of location referenced by `entity_code`.
The following are **all 15 observed signed type values <= 5** in the accepted
state and central organization-unit histories (30 January 2022–19 October
2026) and the details observations of 23–24 October 2026. Checked on
24 October 2026: each value has exactly one supplied `entity_type_name`
across both details observations, including the two blank labels.

These labels come directly from this report's **Entity Type Name** column;
they are not inferred from organization or unit names.

| `entity_type` | Exact supplied `entity_type_name` | Kind of reference |
| ---: | --- | --- |
| `1` | `State` | Geographic entity |
| `2` | `District` | Geographic entity |
| `3` | `Subdistrict` | Geographic entity |
| `4` | `Village` | Geographic entity |
| `5` | `Block` | Geographic entity |
| `-1` | `District Panchayat` | Local body |
| `-2` | `Intermediate Panchayat` | Local body |
| `-3` | `Village Panchayat` | Local body |
| `-4` | `Municipal Corporations` | Local body |
| `-5` | `Municipality` | Local body |
| `-6` | `Notified Area Council` | Local body |
| `-7` | `Town Panchayat` | Local body |
| `-8` | `Cantonment Board` | Local body |
| `0` | `''` (blank) | Unlabelled source value |
| `-100` | `''` (blank) | Unlabelled source value; see below |

Both fields remain strings in the exports. For example, `(entity_type='2',
entity_code='1')` references a district; `entity_code='1'` alone does not
identify which kind of entity is intended. The reference is separate from
the office's own `organization_unit_code` and its `organization_level_code`.

The name lookup in [state_admin_depts](state_admin_depts.md) and
[central_admin_depts](central_admin_depts.md) is for administrative levels:
`entity_type` can match their `administrative_unit_level_code`. Neither
accepted administrative-level history contains a code <= 5 in this review.
Consequently, the labels above are confirmed by `org_unit_details`, not by
those administrative-level tables. The numeric boundary is an observed
pattern; this reference does not establish a universal rule or an exhaustive
LGD enum.

### Blank labels and source-name limitations

- All 659 type-`0` rows in the 24 October details observation also have
  `entity_code='0'`. Preserve the blank type label; do not invent a named
  geographic entity for this value.
- All 194 type-`-100` rows describe international embassy locations in their
  unit names, but their supplied type labels are blank. This suggests an
  international-location reference; it does not establish an official label
  such as `Country`. For example, type `-100`, entity code `1` accompanies
  `EMBASSY OF INDIA(INTERNATIONAL-AFGHANISTAN )`, yet the supplied
  `entity_name` is `Anantnag`. Preserve these source values and do not use
  that name to interpret the reference as a district.

Confirming a type label does not validate every supplied entity code or name.
The details report also has less complete unit coverage than the separate
state/central directories, so its row counts are not their row counts.

To inspect the supplied labels in a downloaded details snapshot:

```sql
SELECT DISTINCT entity_type, entity_type_name
FROM read_parquet('org_unit_details.parquet')
WHERE TRY_CAST(entity_type AS INTEGER) <= 5
ORDER BY TRY_CAST(entity_type AS INTEGER);
```
