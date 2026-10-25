# pri_local_body_wards

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/pri_local_body_wards.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

LGD's PRI-ward report supplies ward codes, names and numbers, plus
the local body, state, body type and higher-parent names. Normalized
identity is `ward_code`; spelling variants and contradictory parent
labels do not create additional wards.

When source labels or state attributes conflict, conversion resolves
them by body code using a PRI register dated at or before the report.
Original variants remain in discrepancy evidence. Unresolved records
are omitted from the normalized daily report, with history able to
retain the previous reliable value as not updated. Reviewed stale
ward/body exclusions apply only within their documented date limits.

## Row identity and conversion

Every ward in the retained 2022–2026 source history has exactly one body
code. Conflicting simultaneous body codes or ward attributes stop
conversion for review; name/state resolution does not choose between
conflicting ward-to-body assignments.

```text
(ward_code)
```

Exact copies collapse. When source rows disagree on a body name, type, state or
higher-parent name, the converter looks up the body **by code** in a supplied
[PRI body register](pri_local_bodies.md) dated at or before the ward report.
Higher-parent names follow parent codes in that register. State code and name
are resolved together; other agreed values remain as reported. Current names
are never used to rewrite older reports.

The original distinct conflicting rows and selected values remain in a separate
Parquet file linked by the conversion receipt's `discrepancy_evidence`. The
receipt pins the reference date and checksum. When a reference is supplied but
cannot resolve a conflict, the affected ward is omitted from this daily snapshot
and counted in `unresolved_source_rows`; it is not asserted to be deleted.
History can retain its previous reliable value and actual source date.
A missing reference input when conflicts need resolution is an error.

**Reviewed exclusion:** 704 stale ward/body pairs are ignored only from
30 January 2022 through 22 November 2023. Their codes have no body-register
match anywhere in the retained history and their contradictory records
subsequently disappear. Original rows remain in discrepancy evidence with
`resolution='ignored'`; the receipt counts `ignored_source_rows`. This rule does
not suppress a corrected record on a later date. The explicit pairs and date
bounds are in [the exclusion rule](../pri_ward_exclusions.py).

Known `Word Code`, `Word Number` and `Disrtict Level Parent Name` header typos
are accepted. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `ward_code` | `VARCHAR` | `Ward Code` | No |
| 2 | `ward_number` | `VARCHAR` | `Ward Number` | No |
| 3 | `ward_name` | `VARCHAR` | `Ward Name (In English)` | No |
| 4 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 5 | `local_body_name` | `VARCHAR` | `Local Body Name` | No |
| 6 | `state_code` | `VARCHAR` | `State Code` | No |
| 7 | `state_name` | `VARCHAR` | `State Name` | No |
| 8 | `ward_name_local` | `VARCHAR` | `Ward Name (In Local)` | No |
| 9 | `local_body_type_name` | `VARCHAR` | `Local Body Type` | No |
| 10 | `district_panchayat_name` | `VARCHAR` | `District Level Parent Name` | No |
| 11 | `intermediate_panchayat_name` | `VARCHAR` | `Intermediate Level Parent Name` | No |
