# constituencies_mapping_urban

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/constituencies_mapping_urban.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This report connects urban wards and local bodies to assembly and
parliamentary constituencies, including reported ECI identifiers and
district/subdistrict paths. A ward lookup can return several rows:
normalized identity includes ward, assembly, subdistrict and district
codes. Body, state and parliamentary parent remain attributes.

The geographic paths can reflect the body's coverage repeated across
its wards, rather than independently established ward locations.
District-only paths and blank assembly references remain visible.
ECI values are a separate identifier namespace and retain the
report's claims; they are not an authoritative correction of LGD codes.

## Row identity and conversion

Blank assembly and ECI codes, and blank district/subdistrict references,
are retained as reported. This report does not establish complete
constituency coverage.

The reported record key is:

```text
(ward_code, assembly_constituency_code, subdistrict_code, district_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

Body, state and parliamentary parent are attributes. District/subdistrict
references describe reported geographic coverage; they do not independently
establish each ward's geography. District is necessary when subdistrict is
blank or zero: Kolkata and Siliguri each supply multiple district paths in
that form. Blank/zero assembly references remain as reported. The
historical key review
found no simultaneous ambiguity for this four-field key across all retained
observations. Any future conflicting parent or other attribute stops conversion.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `ward_code` | `VARCHAR` | `Ward Code` | No |
| 2 | `ward_name` | `VARCHAR` | `Ward Name` | No |
| 3 | `local_body_code` | `VARCHAR` | `Urban Localbody Code` | No |
| 4 | `local_body_name` | `VARCHAR` | `Urban Localbody Name` | No |
| 5 | `local_body_type_name` | `VARCHAR` | `Localbody Type` | No |
| 6 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency code` | No |
| 7 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 8 | `parliament_constituency_eci_code` | `VARCHAR` | `Parliament Constituency ECI Code` | No |
| 9 | `assembly_constituency_code` | `VARCHAR` | `Assembly Constituency Code` | No |
| 10 | `assembly_constituency_name` | `VARCHAR` | `Assembly Constituency Name` | No |
| 11 | `assembly_constituency_eci_code` | `VARCHAR` | `Assembly Constituency ECI Code` | No |
| 12 | `district_code` | `VARCHAR` | `District Code` | No |
| 13 | `district_name` | `VARCHAR` | `District Name` | No |
| 14 | `subdistrict_code` | `VARCHAR` | `Subdistrict Code` | No |
| 15 | `subdistrict_name` | `VARCHAR` | `Subdistrict Name` | No |
| 16 | `state_code` | `VARCHAR` | `State Code` | No |
