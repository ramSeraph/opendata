# constituencies_mapping_pri

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/constituencies_mapping_pri.md) · [API/CLI conventions](../QUERIES.md)

This report connects villages, rural local bodies and
blocks to parliamentary/assembly constituencies, with administrative
and census context. It also supplies reported LGD-to-ECI constituency
identifiers. One village can have several coded associations, and
reviewed block disagreements require retaining `block_code`.

## API

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

## Exact filters

| Value type | Filters |
| --- | --- |
| `assembly` or `parliament` | `constituency_level` |
| Code; scope with `constituency_level` | `constituency_code` |
| Code | `village_code`, `village_census_2011_code`, `local_body_code`, `block_code`, `subdistrict_code`, `subdistrict_census_2011_code`, `district_code`, `district_census_2011_code`, `parliament_constituency_code`, `parliament_constituency_eci_code`, `assembly_constituency_code`, `assembly_constituency_eci_code`, `state_code` |
| Text | `village_name`, `local_body_name`, `block_name`, `subdistrict_name`, `district_name`, `parliament_constituency_name`, `assembly_constituency_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query constituencies_mapping_pri list --limit 5
```
