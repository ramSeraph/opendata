# constituencies_mapping_pri

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/constituencies_mapping_pri.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This report connects villages, rural local bodies and
blocks to parliamentary/assembly constituencies, with administrative
and census context. It also supplies reported LGD-to-ECI constituency
identifiers. One village can have several coded associations, and
reviewed block disagreements require retaining `block_code`.

Assembly-backed and parliamentary-only links remain distinct. Names
are attributes; conflicting body labels resolve through a dated PRI
register, with originals preserved as evidence. ECI values contain
documented errors and reuse, so reverse lookups retain every match.
The retained historical collection ends in October 2022. The scraper has been
restored for current reports; inspect each export's source date, and do not
interpret the collection gap as an unchanged electoral map.

## Row identity and conversion

Blank source references remain as reported.

The reported record key is:

```text
(village_code, local_body_code, block_code, constituency_level, constituency_code)
```

An assembly code other than blank/zero sets the derived fields to `assembly`
and that LGD code. Otherwise they are `parliament` and the parliamentary code.
The reported assembly and parliamentary columns are preserved. Block remains
in the key because some villages are reported under different blocks for the
same body and assembly link; neither assertion is silently discarded.
The dated block-mapping cross-check leaves 25 Tripura villages unresolved,
supporting retention of `block_code` in identity. This preserves reported
associations without treating every block assignment as verified.

Identical records collapse. Conflicting `local_body_name` values require
`--pri-reference` and `--reference-observed-on`, selecting a canonical PRI-body
Parquet dated at or before the report. Resolution joins by body code and state.
A missing or ambiguous reference stops conversion; no arbitrary label is chosen.
The receipt pins the reference and a `discrepancy_evidence` Parquet containing
the original rows. `conflicting_name_rows` counts distinct source variants.
Other attribute conflicts still stop conversion.

The dated key review
confirms that village alone and village/body both collide on distinct coded
associations. The key above preserves distinct blocks and both assembly-backed and PC-only
links, while removing name and administrative-path variants from identity.
Reported ECI identifiers also contain collisions and incorrect values; see the
[ECI lookup notes](../../../lgd-query/docs/datasets/constituencies_mapping_pri.md#eci-code-lookup).
They remain source attributes, not verified electoral identifiers.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name` | No |
| 3 | `village_census_2011_code` | `VARCHAR` | `Village Census 2011 Code` | No |
| 4 | `local_body_code` | `VARCHAR` | `Rural Localbody Code` | No |
| 5 | `local_body_name` | `VARCHAR` | `Rural LocalbodyName` | No |
| 6 | `block_code` | `VARCHAR` | `Block Code` | No |
| 7 | `block_name` | `VARCHAR` | `Block Name` | No |
| 8 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 9 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name` | No |
| 10 | `subdistrict_census_2011_code` | `VARCHAR` | `Subdistrict Census 2011 Code` | No |
| 11 | `district_code` | `VARCHAR` | `District Code` | No |
| 12 | `district_name` | `VARCHAR` | `District Name` | No |
| 13 | `district_census_2011_code` | `VARCHAR` | `District Census 2011 Code` | No |
| 14 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency code` | No |
| 15 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 16 | `parliament_constituency_eci_code` | `VARCHAR` | `Parliament Constituency ECI Code` | No |
| 17 | `assembly_constituency_code` | `VARCHAR` | `Assembly Constituency Code` | No |
| 18 | `assembly_constituency_name` | `VARCHAR` | `Assembly Constituency Name` | No |
| 19 | `assembly_constituency_eci_code` | `VARCHAR` | `Assembly Constituency ECI Code` | No |
| 20 | `state_code` | `VARCHAR` | `State Code` | No |
| 24 | `constituency_level` | `VARCHAR` | Derived | Always computed |
| 25 | `constituency_code` | `VARCHAR` | Derived | Always computed |

IDs 21–23 remain reserved for history provenance and interval fields.
