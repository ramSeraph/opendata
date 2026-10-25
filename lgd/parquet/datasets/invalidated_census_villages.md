# invalidated_census_villages

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/invalidated_census_villages.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

This report lists villages that LGD reports as invalidated, with
village/state codes and names and, where supplied, 2001/2011 census
references. It is a reported status list rather than a dated
invalidation-event log: the first observation of a row does not
establish when invalidation occurred.

The retained history contains one state-only placeholder with no village or
census attributes. It remains reporting context; exclude blank village codes
when counting villages. The record key is `village_code`; state remains an
attribute and filter.
Use the LGD village code, not a census number, when comparing with
[villages](villages.md).

## Row identity and conversion

A blank village code requires every village/census attribute to be empty.
Census columns are optional. State LGD Code/Village LGD Code and the
corresponding English-name header aliases are accepted.

The reported record key is:

```text
(village_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

Across all 1,630 retained observations from 30 January 2022 through 19 October
2026, each of the 6,747 real village codes has one reported state and no
simultaneous conflicting rows. State is not needed to distinguish villages.
The one blank-code row on 24 March 2025 is reporting context, not a village
identity. A report containing distinct blank-code placeholders is rejected
rather than combining their state claims.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `village_code` | `VARCHAR` | `Village Code` | No |
| 2 | `village_name` | `VARCHAR` | `Village Name(In English)` | No |
| 3 | `state_code` | `VARCHAR` | `State Code` | No |
| 4 | `state_name` | `VARCHAR` | `State Name (In English)` | No |
| 5 | `village_census_2001_code` | `VARCHAR` | `Census Code 2001` | Yes → NULL |
| 6 | `village_census_2011_code` | `VARCHAR` | `Census Code 2011` | Yes → NULL |
