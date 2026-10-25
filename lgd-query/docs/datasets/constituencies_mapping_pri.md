# constituencies_mapping_pri

This report connects villages, rural local bodies and
blocks to parliamentary/assembly constituencies, with administrative
and census context. It also supplies reported LGD-to-ECI constituency
identifiers. One village can have several coded associations, and
reviewed block disagreements require retaining `block_code`.

Assembly-backed and parliamentary-only links remain distinct. Names
are attributes; conflicting body labels resolve through a dated PRI
register, with originals preserved as evidence. ECI values contain
documented errors and reuse, so reverse lookups retain every match.
The retained historical collection ends in October 2022. The scraper has been
restored for current reports; inspect each export's source date, and do not
interpret the collection gap as an unchanged electoral map.

## API

```python
from lgd_query.queries import constituencies_mapping_pri

rows = constituencies_mapping_pri.list(db).fetchall()
matches = constituencies_mapping_pri.search(db, "name", mode="contains").fetchall()
```

- `list(db, **filters)` retains every matching source row.
- `by_code(db, code, **filters)` selects `village_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `village_name`.
- `by_census_code(db, code, year=..., **filters)` supports 2011 for the primary entity only.

## ECI code lookup

```python
# db contains a single dated observation as constituencies_mapping_pri.
rows = constituencies_mapping_pri.eci_codes(
    db, level="assembly", constituency_code="2034"
).fetchall()  # Nayagram: reported ECI code 220, LGD state 19
```

`eci_codes(db, *, level, constituency_code=None, state_code=None, eci_code=None)`
accepts `level="assembly"` or `"parliament"`. `constituency_code` is an LGD
code; `eci_code` allows reverse lookup. Filters combine with AND and preserve
leading zeros in strings. No name-reference dataset is needed.

Each result contains `source_dataset`, `state_code`, the level's
`*_constituency_code` and `*_constituency_eci_code`, `lookup_names`, and two flags:

- `conflicting_eci_codes`: the same state/LGD code has several reported ECI codes.
- `eci_code_reused`: the same state/ECI code has several reported LGD codes.

Flags are calculated across the selected report before applying filters. All
competing mappings survive. Repeated village/body rows collapse for this
lookup only; the source report is unchanged. Blank/zero state, LGD or ECI codes
do not produce lookup rows. An empty result means no supplied mapping, not
that the constituency does not exist.

The reviewed historical collection covers **30 January–12 October 2022**. Its last observation
has 388 parliamentary and 3,015 assembly mappings, including four reused ECI
values involving eight constituencies. These are source claims, not a verified
electoral crosswalk; absence of a collision is not proof of accuracy. For
example, the report gives Chanditala ECI code 195, while the
[West Bengal CEO constituency list](https://ceowestbengal.wb.gov.in/Candidate/614)
lists Chanditala as 194 and Jangipara as 195.

For a local file, register one dated snapshot under this dataset's view name
before calling the helper; do not combine observations from different dates.
For release data, `queries.sources(release, "constituencies_mapping_pri")`
exposes the actual source date. The CLI requires an index containing this
report and fails explicitly if it is absent:

```sh
lgd-query constituencies_mapping_pri eci-codes --level assembly --constituency-code 2034 --format json
lgd-query constituencies_mapping_pri eci-codes --level assembly --state-code 6 --eci-code 42 --format json
```

The usual `--cache-dir` and `--observed-on` options apply. The date option is
an exact source-date guard, not an instruction to reconstruct another date.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `village_name` | Supplied `village_name` | None |
| `local_body_name` | Supplied `local_body_name` | None |
| `block_name` | Supplied `block_name` | None |
| `subdistrict_name` | Supplied `subdistrict_name` | None |
| `district_name` | Supplied `district_name` | None |
| `parliament_constituency_name` | Supplied `parliament_constituency_name` | None |
| `assembly_constituency_name` | Supplied `assembly_constituency_name` | None |
| `english` | Supplied `village_name` | None |
| `state_name` | `states.state_name` | `states` |

Lookup keys are explicit and names never serve as join keys:

- `state_name`: `state_code` → `states.state_code`.

Lookup searches add `lookup_names` containing all distinct resolved labels. Multiple labels do not multiply the source row. Missing references do not match. The matching report can have a different date; inspect `queries.sources(...)` before opening it. Supplied columns remain unchanged.

## Exact filters

All supplied filters combine with AND and run before search limits. `None` leaves a filter unused. Text filters use exact source spelling; use `search(field=...)` for normalized name matching.

| Filter | Value |
| --- | --- |
| `constituency_level` | Exact `assembly` or `parliament` |
| `constituency_code` | LGD code in that level; filter level as well |
| `village_code` | Integer or ASCII digit string; zeros preserved |
| `village_name` | Exact string |
| `village_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_code` | Integer or ASCII digit string; zeros preserved |
| `local_body_name` | Exact string |
| `block_code` | Integer or ASCII digit string; zeros preserved |
| `block_name` | Exact string |
| `subdistrict_code` | Integer or ASCII digit string; zeros preserved |
| `subdistrict_name` | Exact string |
| `subdistrict_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `district_code` | Integer or ASCII digit string; zeros preserved |
| `district_name` | Exact string |
| `district_census_2011_code` | Integer or ASCII digit string; zeros preserved |
| `parliament_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `parliament_constituency_name` | Exact string |
| `parliament_constituency_eci_code` | Integer or ASCII digit string; zeros preserved |
| `assembly_constituency_code` | Integer or ASCII digit string; zeros preserved |
| `assembly_constituency_name` | Exact string |
| `assembly_constituency_eci_code` | Integer or ASCII digit string; zeros preserved |
| `state_code` | Integer or ASCII digit string; zeros preserved |

## CLI

```sh
lgd-query constituencies_mapping_pri list --format json
lgd-query constituencies_mapping_pri search NAME --mode fuzzy --cache-dir ./data
lgd-query constituencies_mapping_pri code CODE --help
```

Filters become hyphenated flags (for example `state_code` → `--state-code`).
Use `--field`, `--mode`, `--max-distance`, `--metric`, and `--limit` for search.
All commands support `--cache-dir`, `--observed-on`, and `--format json|table`.
Dataset commands preview 20 rows; use `--limit`, `--all` and `--columns` to
control output. See [CLI conventions](../QUERIES.md#cli) for missing-value
predicates and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/constituencies_mapping_pri.md) and [shared query rules](../QUERIES.md).
