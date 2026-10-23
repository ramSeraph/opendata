# org_unit_coverage

Reported geographic coverage of organization units. Each row is either a supplied
coverage claim or a unit for which no coverage details were supplied. A unit can
cover multiple geographic entities, types and hierarchy levels. These claims do
not describe the location of the unit itself.

## Row identity and conversion

There is no stable claim identifier or enforced unique key. Every source row is
retained, including exact duplicates, alternative labels, full/partial claims
and overlapping report selections. No rows are collapsed or selected as
authoritative. To count units, count distinct
`(organization_unit_code, organization_code, state_code)` rather than rows.

`entity_code` and `entity_name` describe the unit's reported location reference;
this report does not supply its entity type. `covered_entity_*` identifies the
target of a coverage claim. A numeric code is not sufficient to distinguish
entities from different types. Do not infer a type for a missing label.

`report_organization_level_code` and `report_organization_level_name` describe
the report selection. It can return descendant levels, so these fields must not
be treated as each returned unit's own `organization_level_code/name`.
Other shared attributes use the same canonical names and types as the unit
directory and unit-details datasets.

`coverage_details_reported` retains the strings `true` and `false`:

- `true`: a claim was supplied. `covered_entity_code` must be numeric text and
  `coverage_type` must be `F` (full) or `P` (partial). The entity name and type may
  be blank and remain blank.
- `false`: no coverage details were supplied. All four claim fields must be
  empty strings. This does not establish that the unit has no coverage.

The report is not a complete census of organization units. An omitted unit,
organization or claim does not establish deletion. State code `0` and name
`India` identify the Centre's report scope. They do not mean that every covered
entity is in a separate geographic state numbered zero.

All fields remain strings, including organization-specific identifiers, flags,
leading zeroes, quoted names and source blanks. The CSV dialect is explicit,
because quotes and embedded commas can first appear far into a report. Invalid
identifiers, inconsistent flags/claim fields, incomplete rows, and unknown,
duplicate or missing headers fail conversion. Empty exports require review.

## Fields

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

## Released-source review

The [23 October 2026 report](https://github.com/ramSeraph/opendata/releases/download/lgd-latest/org_unit_coverage.23Oct2026.csv.7z)
contains 1,977,782 rows and 585,710 distinct unit/organization/state tuples.
There are 1,759 organization/state scopes and 2,057 report selections, spanning
the Centre and all 36 states/UTs. These counts describe rows actually supplied;
selections returning no rows are not represented by placeholder organizations.

| Finding | Handling |
| --- | --- |
| 538,639 rows have no coverage details. | Retain the unit and scope with blank claim fields and `coverage_details_reported='false'`. |
| 1,439,143 rows contain coverage claims. | Preserve every full/partial claim; counts across hierarchy levels are not counts of distinct places. |
| 51,007 supplied claims have a blank entity type; 58,463 have a blank entity name. | Preserve the incomplete claims. Do not fabricate names or infer target types. |
| Organization-specific identifiers are often blank and can contain letters or leading zeroes. | Retain text verbatim; do not treat these as numeric LGD identifiers. |
| No exact duplicate rows occur in this release. | The converter nevertheless preserves source multiplicity if future reports repeat claims. |

The archive is 16,738,471 bytes; its CSV member is 393,474,324 bytes.
The standalone Parquet file is **15,846,526 bytes (15.1 MiB)**. An independent
CSV reader checked every record's column count. A separate source-to-Parquet
comparison verified all 16 field values, row multiplicity and field IDs for
all 1,977,782 rows; no rows were collapsed.
Pinned SHA-256 hashes:

```text
archive: dc78b8c18dd90f8247fe97fd54b70536c0d893967cdba0d74d6ee21a9d664dbf
CSV:     0d5197faa36f27d102271e420746541835d901156b9fb38c4a580bae9cded401
Parquet: 76c82136807cafa568649bada7692c5bed1eb2743b30f542735eb80d2d14c011
```

The standalone output contains no inferred deletions, carried rows, observation
ledger or validity intervals. See the [common conversion rules](../README.md#schemas-and-interpretation).

```sql
SELECT covered_entity_type, coverage_type, count(*) AS reported_claims
FROM read_parquet('org_unit_coverage.parquet')
WHERE coverage_details_reported = 'true'
GROUP BY ALL;
```
