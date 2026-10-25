# tlb_villages

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/tlb_villages.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This is LGD's Gram Panchayat/TLB village-mapping report. It contains
both PRI gram panchayats and traditional local bodies, with village,
block, administrative-path and census references. The retained name
`tlb_villages` does not restrict the rows to traditional bodies.

Resolve body codes against both [pri_local_bodies](pri_local_bodies.md)
and [traditional_local_bodies](traditional_local_bodies.md). Supplied
body type codes/names classify the body, while block and village codes
identify separate entities. The misleading source body-census field
is omitted from normalized output; the state, district, subdistrict
and village census fields remain.

## Scope and local-body identifiers

The dataset keeps the name `tlb_villages`, but contains **both PRI gram
panchayats and traditional local bodies**. LGD's older headers explicitly say
`Gram Panchayat/TLB`; the newer layout uses `Local Body`. The filename is not a
filter for traditional bodies. For example, Pohane (`183238`) and Wathephal
(`184413`) are Maharashtra PRI bodies with type `3`, Village Panchayat.

Resolve `local_body_code` against both [PRI](pri_local_bodies.md) and
[traditional](traditional_local_bodies.md) registers. PRI, traditional and urban
bodies share the local-body identifier namespace, as described by
[LGD](https://panchayat.gov.in/en/lgd/). A body's type classifies that identifier;
it is not needed to distinguish it from a different body's code. Village and
development-block codes identify different entities and must not be joined to
local bodies merely because their numbers match.

The retained PRI, traditional and urban histories, starting 30 January 2022 and
ending 15, 21 and 15 October 2026 respectively, contain no code shared between
any two registers. This is an observed check of the retained data, not evidence
of the database's sequence-allocation implementation.

## Row identity and conversion

Local-body type code/name are optional but must be supplied together.
When both state-name columns are present, their values must agree
exactly. Blank village, subdistrict, block and body references require
consistent empty names and dependent fields.

The reported record key is:

```text
(village_code, block_code, local_body_code, state_code, district_code, subdistrict_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name (In English)` | No |
| 3 | `local_body_code` | `VARCHAR` | `Gram Panchayat/ TLB Code` | No |
| 4 | `local_body_name` | `VARCHAR` | `Gram Panchayat/ TLB (In English)` | No |
| 5 | `local_body_type_code` | `VARCHAR` | `Gram Panchayat/ TLB Type Code` | Yes → NULL |
| 6 | `local_body_type_name` | `VARCHAR` | `Gram Panchayat/ TLB Type Name` | Yes → NULL |
| 7 | `block_code` | `VARCHAR` | `Block Code` | No |
| 8 | `block_name` | `VARCHAR` | `Block Name (In English)` | No |
| 9 | `subdistrict_code` | `VARCHAR` | `Sub-district Code` | No |
| 10 | `subdistrict_name` | `VARCHAR` | `Sub-district Name (In English)` | No |
| 11 | `district_code` | `VARCHAR` | `District Code` | No |
| 12 | `district_name` | `VARCHAR` | `District Name (In English)` | No |
| 13 | `state_code` | `VARCHAR` | `State Code` | No |
| 14 | `state_name` | `VARCHAR` | `State Name` | No |
| 15 | `state_census_2011_code` | `VARCHAR` | `State Census 2011 Code` | No |
| 16 | `district_census_2011_code` | `VARCHAR` | `District Census 2011 Code` | No |
| 17 | `subdistrict_census_2011_code` | `VARCHAR` | `Sub-district Census 2011 code` | No |
| 18 | `village_census_2011_code` | `VARCHAR` | `Village Census 2011 Code` | No |

## Ignored source field

`Gram Panchayat/TLB Census 2011 Code` (newer header: `Local Body 2011 Code`)
is recognized but omitted from normalized output. Its former canonical name
was `local_body_census_2011_code`, with field ID 19; that ID remains retired.
The source header stays in provenance, and conversion receipts list the field
in `omitted_source_fields`.

Before omission, the 18 October 2026 snapshot had `0` in 656,093 of 656,121 rows. The other 28
rows cover 18 Maharashtra bodies and contain mixed identifiers: Bhor's
`526867` is a village census code; Kurhe PN's `176484` repeats its LGD body
code, while its village census code is `527114`. Pohane supplies `163` and
Wathephal supplies `5` (formerly `000163` and `000005`). These values do not
provide a consistent local-body census identifier.

The village, subdistrict, district and state census fields remain in the
schema. No body census value is inferred or copied into those fields.
