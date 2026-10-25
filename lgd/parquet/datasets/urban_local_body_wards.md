# urban_local_body_wards

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/urban_local_body_wards.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

LGD's urban-ward register identifies each ward by `ward_code` and
supplies its name, ward number, local-body code/name and state. The
body reference connects to [urban_local_bodies](urban_local_bodies.md).

Ward numbers are source labels and are not interchangeable with ward
codes. This report does not supply district or subdistrict assignments.
Geographic paths in [constituencies_mapping_urban](constituencies_mapping_urban.md)
come from a separate report and cannot be verified against this register
alone. Any census code here belongs to the body.

## Row identity and conversion

The body census code is optional; both Census Code 2011 and the canonical
source header are accepted. Ward numbers remain text.

The reported record key is:

```text
(ward_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `ward_code` | `VARCHAR` | `Ward Code` | No |
| 2 | `ward_number` | `VARCHAR` | `Ward Number` | No |
| 3 | `ward_name` | `VARCHAR` | `Ward Name` | No |
| 4 | `local_body_code` | `VARCHAR` | `Local Body Code` | No |
| 5 | `local_body_name` | `VARCHAR` | `Local Body Name` | No |
| 6 | `state_code` | `VARCHAR` | `State Code` | No |
| 7 | `state_name` | `VARCHAR` | `State Name` | No |
| 8 | `local_body_census_2011_code` | `VARCHAR` | `Census 2011 Code` | Yes → NULL |
