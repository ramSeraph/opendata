# gp_mapping

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/gp_mapping.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This report links villages to gram panchayats/local bodies and
supplies their administrative and census context. Each association
is identified by `(village_code, local_body_code)`. A village can have
more than one local-body link; state, district and subdistrict are
attributes of the reported association.

Resolve village and body references through [villages](villages.md)
and [pri_local_bodies](pri_local_bodies.md). Rows that identify a
village but supply no body remain as incomplete evidence. Rows with
no village and only hierarchy context are omitted after validation,
so they do not appear as fictitious village/body associations.

## Row identity and conversion

Hierarchy-only rows with blank village codes are omitted after validating
their empty dependent fields; the receipt counts `ignored_source_rows`.
A whitespace-only body code is retained only with an empty body name.
Census-header word-order variants are accepted.

The reported record key is:

```text
(village_code, local_body_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name (in English)` | No |
| 3 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 4 | `local_body_name` | `VARCHAR` | `Local Body Name (in English)` | No |
| 5 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 6 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name (in English)` | No |
| 7 | `district_code` | `VARCHAR` | `District Code` | No |
| 8 | `district_name` | `VARCHAR` | `District Name (in English)` | No |
| 9 | `state_code` | `VARCHAR` | `State Code` | No |
| 10 | `state_name` | `VARCHAR` | `State Name` | No |
| 11 | `village_census_2011_code` | `VARCHAR` | `Village Census 2011 Code` | No |
| 12 | `village_census_2001_code` | `VARCHAR` | `Village Census 2001 Code` | No |
| 13 | `subdistrict_census_2011_code` | `VARCHAR` | `Subdistrict Census Code 2011` | No |
| 14 | `subdistrict_census_2001_code` | `VARCHAR` | `Subdistrict Census Code 2001` | No |
| 15 | `district_census_2011_code` | `VARCHAR` | `District Census 2011 Code` | No |
| 16 | `district_census_2001_code` | `VARCHAR` | `District Census 2001 Code` | No |
