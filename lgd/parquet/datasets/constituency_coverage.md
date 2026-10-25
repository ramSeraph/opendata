# constituency_coverage

This report links typed geographic entities to parliamentary or
assembly constituencies. `entity_type` is District, SubDistrict,
Village, Localbody or Ward; it determines which register an
`entity_code` refers to. A supplied assembly code identifies an
assembly link; otherwise the row is a parliamentary-only link.

Full/partial coverage is an attribute of the association. When both
values are reported for the same association, normalized
`coverage_type` is NULL and the original claims remain recoverable.
Reports known to omit alternative links are incomplete: standalone
Parquet contains supplied associations, while history can retain
older alternatives as not updated. These flags do not quantify
population or identify individual covered children.

## Row identity and conversion

A blank or zero assembly reference requires an empty assembly name.
An extra State Name English column is ignored only if all its values
are empty. Source blanks or unknown coverage flags are rejected.

The reported record key is:

```text
(entity_code, entity_type, constituency_level, constituency_code)
```

`constituency_level` and `constituency_code` are derived fields: an assembly
code other than blank/zero produces `assembly` and that LGD code; otherwise
`parliament` and the parliamentary LGD code. Thus a PC-only link and an
assembly link with the same numeric code remain separate. Parliamentary
parent and state are attributes of an assembly link, not additional identities.
Their original source columns remain unchanged. IDs 11–13 are reserved for
history metadata; the derived fields use IDs 14–15.

Identical records collapse. Full/Partial values are attributes, not separate
identities. If both occur for this key and all other attributes agree, the
converter emits one row with `coverage_type=NULL`. This NULL means exactly
those two reported claims; blank or unknown source flags are rejected. It is
not a third source value or a decision about which claim is correct.

The conversion receipt records `conflicting_coverage_rows` and links a
checksum-verified `discrepancy_evidence` Parquet containing both distinct
original rows. `collapsed_rows` includes exact duplicates and the extra
Full/Partial claim merged into each association. Conflicts in any other
attribute still stop conversion.

All rows come from the selected report. Common [conversion rules](../README.md#schemas-and-interpretation)
cover text preservation, blanks, optional columns and strict validation.

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `entity_code` | `VARCHAR` | `Entity Code` | No |
| 2 | `entity_name` | `VARCHAR` | `Entity Name` | No |
| 3 | `entity_type` | `VARCHAR` | `Entity Type` | No |
| 4 | `parliament_constituency_code` | `VARCHAR` | `Parliament Constituency Code` | No |
| 5 | `parliament_constituency_name` | `VARCHAR` | `Parliament Constituency Name` | No |
| 6 | `assembly_constituency_code` | `VARCHAR` | `Assembly Constituency Code` | No |
| 7 | `assembly_constituency_name` | `VARCHAR` | `Assembly Constituency Name` | No |
| 8 | `coverage_type` | `VARCHAR` | `Coverage Type` | No |
| 9 | `state_code` | `VARCHAR` | `State Code` | No |
| 10 | `state_name` | `VARCHAR` | `State Name` | No |
| 14 | `constituency_level` | `VARCHAR` | Derived | Always computed |
| 15 | `constituency_code` | `VARCHAR` | Derived | Always computed |

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
