# constituencies_mapping_urban

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/constituencies_mapping_urban.md) · [API/CLI conventions](../QUERIES.md)

This report connects urban wards and local bodies to assembly and
parliamentary constituencies, including reported ECI identifiers and
district/subdistrict paths. A ward lookup can return several rows:
normalized identity includes ward, assembly, subdistrict and district
codes. Body, state and parliamentary parent remain attributes.

The normalized record key is `(ward_code, assembly_constituency_code,
subdistrict_code, district_code)`. `by_code` selects all associations for a
ward without collapsing their constituency or geographic differences.

## API

- `by_code(db, code, **filters)` selects `ward_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `ward_name`.

## ECI code lookup

```python
rows = constituencies_mapping_urban.eci_codes(
    db, level="assembly", state_code="6", eci_code="42"
).fetchall()
```

`eci_codes(db, *, level, constituency_code=None, state_code=None, eci_code=None)`
returns distinct reported LGD/ECI mappings from this view. Levels are `assembly`
and `parliament`; `constituency_code` is an LGD code. Optional filters combine
with AND. The result includes `source_dataset`, `state_code`, the level's
`*_constituency_code` and `*_constituency_eci_code`, distinct `lookup_names`,
`conflicting_eci_codes` (several ECI codes per state/LGD code), and
`eci_code_reused` (several LGD codes per state/ECI code).

The flags consider the full selected view before filtering. Competing claims
are retained, repeated ward/body mappings collapse, and blank/zero codes are
excluded from this lookup. No source rows are modified. Supply one dated
observation, not a union of history intervals.

This is an LGD-reported crosswalk, not a verified ECI register. An unflagged
mapping may still be wrong or stale. The retained 19 October 2026 observation,
for example, reports ECI 195 for Chanditala; the official West Bengal list
uses 194. Jangipara is absent from that urban observation, so the lookup cannot
detect the collision visible in the [PRI report](constituencies_mapping_pri.md#eci-code-lookup).
The [West Bengal CEO constituency list](https://ceowestbengal.wb.gov.in/Candidate/614)
provides the official values for that comparison.

```sh
lgd-query constituencies_mapping_urban eci-codes --level assembly --state-code 6 --eci-code 42 --format json
```

Use `queries.sources(release, "constituencies_mapping_urban")` to inspect source
dates and open the report. `--cache-dir` and `--observed-on` work as for other
commands; the latter checks the report date without reconstructing history.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `ward_name` | Supplied `ward_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `local_body_type_name` | Supplied `local_body_type_name` | None |
| `parliament_constituency_name` | Supplied `parliament_constituency_name` | None |
| `assembly_constituency_name` | Supplied `assembly_constituency_name` | None |
| `district_name` | Supplied `district_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `english` | Supplied `ward_name` | None |
| `state_name` | `states.state_name` | `states` |

Lookup keys are explicit and names never serve as join keys:

- `state_name`: `state_code` → `states.state_code`.

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `ward_code`, `local_body_code`, `parliament_constituency_code`, `parliament_constituency_eci_code`, `assembly_constituency_code`, `assembly_constituency_eci_code`, `district_code`, `subdistrict_code`, `state_code` |
| Text | `ward_name`, `local_body_name`, `local_body_type_name`, `parliament_constituency_name`, `assembly_constituency_name`, `district_name`, `subdistrict_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query constituencies_mapping_urban list --limit 5
```
