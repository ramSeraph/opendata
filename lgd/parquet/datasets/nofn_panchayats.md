# nofn_panchayats

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/nofn_panchayats.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This retired report lists panchayats/local bodies in the National
Optical Fibre Network (NOFN) project, with body codes/names, state and
named district/subdistrict paths. It includes reported PRI and
traditional bodies. One body can have several named paths; district
and subdistrict codes are not supplied.

Membership does not establish operational fibre, service availability
or completeness of the local-body register. The retained source ends
in December 2024. Resolve bodies against the PRI and traditional
registers where possible, and retain unmatched parent names without
inventing codes.

## Row identity and conversion

`SR.NO` is accepted as the discarded row serial.

The reported record key is:

```text
(local_body_code, state_code, district_name, subdistrict_name)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 2 | `local_body_name` | `VARCHAR` | `Local Body Name (In English)` | No |
| 3 | `district_name` | `VARCHAR` | `District Name` | No |
| 4 | `subdistrict_name` | `VARCHAR` | `Sub District Name(In English)` | No |
| 5 | `state_code` | `VARCHAR` | `State Code` | No |
| 6 | `state_name` | `VARCHAR` | `State Name` | No |
