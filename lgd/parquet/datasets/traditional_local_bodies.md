# traditional_local_bodies

This register describes traditional local bodies, their state and
reported district/intermediate parent paths. The institutions and
names vary by state. `local_body_level` gives District, Intermediate
or Village; `local_body_type_code` and `local_body_type_name`, when
supplied, describe the kind of body. Older reports supply types that newer layouts may omit.

A body can have several reported parent paths. Parent resolution needs
both this register and [pri_local_bodies](pri_local_bodies.md). In the
reviewed 23 October 2026 snapshot, some Tripura rows reference PRI parents,
while Meghalaya lists village-level bodies and district councils without
linking their parent codes.
Preserve those unresolved relationships; a successful name lookup
alone does not verify the hierarchy.

## Row identity and conversion

At least one of type code or level must be supplied. An absent type
field becomes NULL, and blank parent codes are permitted.

`local_body_code` identifies a body. The **reported parent-path row key** is:

```text
(local_body_code, district_panchayat_code, intermediate_panchayat_code)
```

The extra columns preserve competing source assertions; they do not form a new
body identifier. On 31 January 2022, for example, Golakpur (`253928`) appears
under district-parent codes `261502` and `261503`, with intermediate parent
`261496` in both rows. A body-only row key would discard one assertion. The
23 October 2026 report has one path per body, but that is not true across the
history. Use `count(DISTINCT local_body_code)` for bodies and `count(*)` for
reported paths.

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Localbody Code` | No |
| 2 | `local_body_version` | `INTEGER` | `Localbody Version` | Yes → NULL |
| 3 | `local_body_name` | `VARCHAR` | `Localbody Name (In English)` | No |
| 4 | `local_body_name_local` | `VARCHAR` | `Localbody Name (In Local)` | Yes → NULL |
| 5 | `local_body_type_code` | `VARCHAR` | `Localbody Type Code` | Yes → NULL |
| 6 | `local_body_type_name` | `VARCHAR` | `Localbody Type Name` | Yes → NULL |
| 7 | `district_panchayat_code` | `VARCHAR` | `District Panchayat Code` | No |
| 8 | `intermediate_panchayat_code` | `VARCHAR` | `Intermediate/Block Panchayat Code` | No |
| 9 | `state_code` | `VARCHAR` | `State Code` | No |
| 10 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 11 | `local_body_level` | `VARCHAR` | `Local Body Level` | Yes → NULL |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.

## Parent references

The current export calls these source fields `District Level TLB Code` and
`Intermediate/Block Level TLB Code`; they map to the canonical
`district_panchayat_code` and `intermediate_panchayat_code`. These are parent
**local-body** codes, not administrative district or subdistrict codes. Despite
the canonical `panchayat` names, parents can be in either
`traditional_local_bodies` or [pri_local_bodies](pri_local_bodies.md).

Resolve either parent field against `local_body_code` in **both** registers,
with matching `state_code`. Keep distinct names from both sources if they
disagree. Zero and blank codes mean no supplied parent reference; do not join
them to a body or infer a missing link from a similar name. The
[query helper](../../../lgd-query/docs/datasets/traditional_local_bodies.md)
implements this lookup without multiplying the source rows or changing parent
codes. Finding a name does not establish that the reported relationship is
correct.

## State-wise levels and names

The following counts describe the **23 October 2026** snapshot: 14,163 bodies
in eight states/UTs. `District`, `Intermediate` and `Village` are reported levels,
not body types. The current scraper combines the three level-specific exports.
A dash means this report has no rows at that level; it is not a claim about the
state's legal or complete institutional structure.

| State/UT (code) | District | Intermediate | Village | Parent links supplied in this report |
| --- | ---: | ---: | ---: | --- |
| Nagaland (`13`) | — | — | 1,351 | Village parent codes are zero. |
| Manipur (`14`) | 6 | — | 3,649 | Villages reference district-level TLBs. |
| Mizoram (`15`) | — | — | 830 | Village parent codes are zero. |
| Tripura (`16`) | 1 | 40 | 587 | Both TLB and PRI parents occur; see the exception below. |
| Meghalaya (`17`) | 3 | — | 7,026 | Village parent codes are zero despite the district councils being listed. |
| Assam (`18`) | 3 | — | 465 | Villages reference district-level TLBs. |
| West Bengal (`19`) | 1 | — | — | Only the district-level body is listed. |
| Andaman And Nicobar Islands (`35`) | — | 7 | 194 | Villages reference intermediate-level TLBs; district parents are zero. |

### Names from older reports

The current snapshot supplies **no type codes or type names**: both columns
are NULL throughout. The names below come from the imported **30 January
2022–21 October 2026 history**, where older layouts supplied them. They explain
the state-specific terminology; they are not values to fill into current rows.
Type codes are distinct from the three level labels and from body identifiers.
To place names in the columns below, we matched current body codes and states
to their older typed rows. This describes names previously reported for bodies
now listed at each level; it does not infer a legal hierarchy or restore missing
type values. Nineteen current Nagaland bodies and six Meghalaya bodies have no
older supplied type in this history, so the names do not cover every current row.

| State/UT | District: historical type code and name | Intermediate: historical type code and name | Village: historical type code and name |
| --- | --- | --- | --- |
| Nagaland | — | — | `12`: Village Development Board |
| Manipur | `10`: Autonomous District Council | — | `17`: Village Authority |
| Mizoram | — | — | `11`: Village Council |
| Tripura | `13`: Tripura Tribal areas Autonomous District Council / Tripura tribal areas autonomous District Council | `14`: Block Advisory Council / Block Advisory Committee | `11`: Village Council |
| Meghalaya | `10`: Autonomous District Council | — | `22`: Village Employment Council / Village Employment council |
| Assam | `10`: Autonomous District Council; previously also `18`: Territorial Council | — | `16`: Village Development Committee; previously also `15`: VCDC |
| West Bengal | `20`: Constitutional Body / Gorkhaland Territorial Administration | — | — |
| Andaman And Nicobar Islands | — | `19`: Tribal Council | `11`: Village Council |

Slashes show alternative labels reported for one type code, not additional
tiers. Assam's type `16` also has a source spelling with two spaces between
`Development` and `Committee`; conversion preserves it. Older Meghalaya reports
also contain `23`: Area Employment Council, which has no matching current body
in this table and no history interval on or after 2 April 2025. Assam's types `15` and `18`
have none on or after 3 April 2025. These are changes in the reports, not evidence
of the dates on which institutions were legally abolished or reorganized.

### Tripura: mixed TLB and PRI parent references

The snapshot lists one district-level TLB, 40 intermediate-level TLBs and 587
village-level TLBs. Most village paths resolve within the TLB register; **33
village rows instead reference PRI bodies at both parent levels**. These are
the same 33 rows for the district and intermediate lookups.

For comparison, Bagmara (`253794`) references Ambassa Bac (`6918`) and the
Tripura Tribal Areas Autonomous District Council (`6910`), both TLBs.
Deoracherra (`253927`) references Gournagar (`2886`) and Unakoti (`589`), both
PRI bodies in the same state's register.

This is an unresolved source oddity. Preserve the asserted codes and resolve
their names, while treating the result as a reported relationship. Do not
silently move those 33 rows under the tribal council or interpret a successful
lookup as confirmation that their PRI parentage is correct.

### Meghalaya: listed tiers without connecting parent links

The snapshot contains **three district councils and 7,026 village-level bodies**,
but every village row has `0` in both parent fields. Listing district and
village tiers together does not provide the edges connecting them. The older
type vocabulary also includes Area Employment Councils (`23`), while the
current report lists no intermediate-level rows.

The district-level rows are Garo Hills Adc (`299398`), Jaintia Hills Adc
(`299404`) and Khasi Hills Adc (`299405`). Their presence does not tell us which
village-level body belongs to which council.

Keep these village bodies unresolved in a hierarchy built from parent codes.
Do not infer a district-council parent from the village name or state, insert
the old Area Employment Council tier, or treat the zero codes as bodies. The
report alone cannot distinguish an intentionally omitted relationship from
missing or defective source data.

## Evidence and reproduction

Counts and parent lookups above use the [23 October TLB snapshot](https://github.com/ramSeraph/opendata/releases/download/lgd-parquet-latest/traditional_local_bodies.2026-10-23.34587f829b99e981.parquet)
and [PRI snapshot from the same date](https://github.com/ramSeraph/opendata/releases/download/lgd-parquet-latest/pri_local_bodies.2026-10-23.d55b3f55f3413115.parquet).

With both snapshot views loaded, this query lists TLB rows whose supplied
district parent is found only in the PRI register. Substitute
`intermediate_panchayat_code` to inspect intermediate parents:

```sql
SELECT t.local_body_code, t.local_body_name, t.district_panchayat_code,
       p.local_body_name AS reported_parent_name
FROM traditional_local_bodies t
JOIN pri_local_bodies p
  ON p.local_body_code = t.district_panchayat_code
 AND p.state_code = t.state_code
WHERE t.district_panchayat_code NOT IN ('', '0')
  AND NOT EXISTS (
    SELECT 1 FROM traditional_local_bodies parent
    WHERE parent.local_body_code = t.district_panchayat_code
      AND parent.state_code = t.state_code
  );
```

Raw SQL joins can multiply rows when a parent register has alternative rows;
the query helper instead collects distinct labels in `lookup_names`.
