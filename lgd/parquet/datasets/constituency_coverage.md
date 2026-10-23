# constituency_coverage

One reported entity/constituency/coverage claim. Entity types are District, SubDistrict, Village, Localbody and Ward; coverage is Fully Covered or Partly Covered. A blank or zero assembly reference requires an empty assembly name. An extra State Name English column is ignored only if every value is empty. Reports known to omit alternative links are still incomplete: standalone conversion emits only the supplied claims.

## Row identity and conversion

The reported record key is:

```text
(entity_code, entity_type, parliament_constituency_code, assembly_constituency_code, state_code, coverage_type)
```

Identical records collapse. Conflicting attributes for this key are rejected;
the converter does not choose one conflicting row as authoritative.

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

“Column may be absent” refers to the header, not whether a supplied value may
be blank. Code validation and placeholder rules still apply to supplied values.
