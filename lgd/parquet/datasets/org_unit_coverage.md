# org_unit_coverage

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/org_unit_coverage.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This combined state/central report lists places an organization unit is reported
to cover, or explicitly says that coverage details were not supplied.
`covered_entity_*` describes the target. `entity_code` and `entity_name` describe
the office's location reference, whose type is not supplied here. State scope
`0` denotes central organizations.

One unit can cover several targets and entity types. No-details rows do not mean
zero coverage, and absence from this report does not establish deletion.

## Row identity

```text
(organization_unit_code, covered_entity_type, covered_entity_code)
```

The other fields are attributes, including names, full/partial coverage,
organization/state context and the selected report level. Exact duplicate rows
collapse; conversion records the raw and collapsed counts. Conflicting attributes
for one key reject the report rather than choosing a claim or adding names and
flags to its identity. The raw CSV remains the original source evidence.

Both retained reports, **23–24 October 2026**, contain **1,977,782 unique keys**
and **585,710 distinct units**, with no conflicting keys or exact duplicates.
This supports the chosen identity; it does not prove that LGD's claims are correct.

Count units with `COUNT(DISTINCT organization_unit_code)`. Row counts count
associations or no-details rows, not distinct places.

## Missing details and target types

| Source value | Meaning and handling |
| --- | --- |
| `coverage_details_reported='true'` | A claim exists. Target code must be numeric text; `coverage_type` is `F` (full) or `P` (partial). |
| A claim has a blank target type or name | Preserve the blank. A missing type leaves the target's namespace unresolved; do not infer an entity-table join from its numeric code. |
| `coverage_details_reported='false'` | No details were supplied. All four claim fields are empty; the key is `(unit_code, '', '')`. This does not establish zero coverage. |

There are **51,007 claims with blank target types**, **58,463 with blank target
names**, and **538,639 no-details rows** in each retained report. These remain
in the normalized data. A code appearing under different target types identifies
distinct associations.

## Fields

All fields remain strings, preserving leading zeros, signed location sentinels,
source blanks, quoted names and organization-specific identifiers. Required
columns, flags and claim consistency are validated. Empty or malformed reports
fail conversion without replacing an earlier output.

The headers are those of our scraped CSV. Fields 11–12 are request metadata
added by the scraper; the other fields come from LGD's returned rows.

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `organization_unit_code` | `VARCHAR` | `Org Unit Code` | No |
| 2 | `organization_unit_name` | `VARCHAR` | `Org Unit Name (In English)` | No |
| 3 | `entity_code` | `VARCHAR` | `Entity Code` | No |
| 4 | `entity_name` | `VARCHAR` | `Entity Name` | No |
| 5 | `organization_unit_specific_code` | `VARCHAR` | `Org Specific Code` | No |
| 6 | `covered_entity_code` | `VARCHAR` | `Covered Entity Code` | No |
| 7 | `covered_entity_name` | `VARCHAR` | `Covered Entity Name` | No |
| 8 | `covered_entity_type` | `VARCHAR` | `Covered Entity Type` | No |
| 9 | `coverage_type` | `VARCHAR` | `Coverage Type` | No |
| 10 | `coverage_details_reported` | `VARCHAR` | `Coverage Details Reported` | No |
| 11 | `report_organization_level_code` | `VARCHAR` | `Report Org Located Level Code` | No |
| 12 | `report_organization_level_name` | `VARCHAR` | `Report Org Level Specific Name` | No |
| 13 | `organization_code` | `VARCHAR` | `Base Organization Code` | No |
| 14 | `organization_name` | `VARCHAR` | `Base Organization Name` | No |
| 15 | `state_code` | `VARCHAR` | `State Code` | No |
| 16 | `state_name` | `VARCHAR` | `State Name` | No |

## Report selection and organization-specific identifiers

`report_organization_level_code/name` identifies the level selected when requesting
the report. A selection can return descendant units; it is not each office's own
organizational level. For example, Vijayawada postal division (`1991926`) has
own level `5385` in `central_org_units`, but is returned under the Postal Circles
selection `5383`. Keep selection fields as collection provenance; use the unit
directory for the office's own level.

`organization_unit_specific_code` is an organization-defined identifier, not an
LGD unit code or a universal PIN-code field. Vijayawada postal division reports
`520001`; other units can supply blanks, letters or leading zeros. Its meaning
and uniqueness require organization-specific evidence.

## Querying

```sql
SELECT covered_entity_type, coverage_type, count(*) AS reported_claims
FROM read_parquet('org_unit_coverage.parquet')
WHERE coverage_details_reported = 'true'
GROUP BY ALL;
```

The [query API](../../../lgd-query/docs/datasets/org_unit_coverage.md) can resolve
recognized target types against their entity registers. Standalone conversion
uses only the selected report; see the
[common conversion rules](../README.md#schemas-and-interpretation).
