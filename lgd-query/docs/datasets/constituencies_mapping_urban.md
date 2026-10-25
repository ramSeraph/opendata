# constituencies_mapping_urban

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

The normalized record key is `(ward_code, assembly_constituency_code,
subdistrict_code, district_code)`. `by_code` selects all associations for a
ward without collapsing their constituency or geographic differences.

## API

```python
from lgd_query.queries import constituencies_mapping_urban

rows = constituencies_mapping_urban.list(db).fetchall()
matches = constituencies_mapping_urban.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
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

Lookup searches add `lookup_names` containing all distinct resolved labels. Multiple labels do not multiply the source row. Missing references do not match. The matching report can have a different date; inspect `queries.sources(...)` before opening it. Supplied columns remain unchanged.

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `ward_code` | Integer or ASCII digit string; zeros preserved |
| `ward_name` | Exact string |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `local_body_type_name` | Exact string |
| `parliament_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `parliament_constituency_name` | Exact string |
| `parliament_constituency_eci_code` | Integer or ASCII digit string; zeros preserved |
| `assembly_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `assembly_constituency_name` | Exact string |
| `assembly_constituency_eci_code` | Integer or ASCII digit string; zeros preserved |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `subdistrict_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_name` | Exact string |
| `state_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query constituencies_mapping_urban list --format json
lgd-query constituencies_mapping_urban search NAME --mode fuzzy --cache-dir ./data
lgd-query constituencies_mapping_urban code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/constituencies_mapping_urban.md) and [shared query rules](../QUERIES.md).
