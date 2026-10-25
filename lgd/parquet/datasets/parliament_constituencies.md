# parliament_constituencies

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/parliament_constituencies.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

LGD's parliamentary-constituency register supplies each
`parliament_constituency_code`, its name and state code/name. The LGD
constituency code identifies the row; state is an attribute.

This register does not supply ECI constituency numbers. The PRI and
urban constituency-mapping reports supply reported LGD-to-ECI links,
with separate source dates and ambiguity concerns. Geographic
associations are available in [constituency_coverage](constituency_coverage.md).

## Row identity and conversion

Empty assembly columns in some layouts are dropped only after validating
that all their values are blank. Serials must be contiguous and start
at 1 or the recognized defective prefix 81. A precise timestamp-only
footer may be ignored. Missing prefix rows are reported in the receipt
and are not fabricated.

The reported record key is:

```text
(parliament_constituency_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency Code` | No |
| 2 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 3 | `state_code` | `VARCHAR` | `State Code` | No |
| 4 | `state_name` | `VARCHAR` | `State Name` | No |
