# assembly_constituencies

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/assembly_constituencies.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

LGD's assembly-constituency register supplies an assembly's code
and name together with parliamentary-constituency and state references.
`assembly_constituency_code` identifies the row; the parliamentary
parent and state are attributes. Parliamentary-only placeholders
with no assembly code or name are omitted.

These are LGD identifiers. ECI numbers are supplied separately in the
PRI and urban constituency-mapping reports, where some reported
mappings are ambiguous. Use [constituency_coverage](constituency_coverage.md)
for links from geographic entities to constituencies.

## Row identity and conversion

Rows with both assembly code and name blank are omitted and counted in
`ignored_source_rows`; a blank code with a populated name is rejected.
Serials must be contiguous and start at 1 or the recognized defective
prefix 81. A precise timestamp-only footer may be ignored. Missing
prefix rows are reported in the receipt and are not fabricated.

The reported record key is:

```text
(assembly_constituency_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `assembly_constituency_code` | `VARCHAR` | `Assembly Constituency Code` | No |
| 2 | `assembly_constituency_name` | `VARCHAR` | `Assembly Constituency Name` | No |
| 3 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency Code` | No |
| 4 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 5 | `state_code` | `VARCHAR` | `State Code` | No |
| 6 | `state_name` | `VARCHAR` | `State Name` | No |
