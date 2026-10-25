# Query guide

[Start here](../README.md) · [Dataset index](datasets/README.md) · [Reader APIs](READER.md)

## Experimental status

`lgd_query.queries` and dataset-specific CLI commands are **experimental**,
available from 0.2.0. Arguments, result columns, lookup rules and interpretations
of dataset relationships may change. Metadata, verified downloads, `connect()`
and free-form SQL are separate reader interfaces.

## Choose an operation

| Python helper | CLI command | Result |
| --- | --- | --- |
| `list(db, **filters)` | `DATASET list` | Matching report rows |
| `by_code(db, code, **filters)` | `DATASET code CODE` | All matches for the dataset's primary lookup code |
| `by_id(db, transaction_id, **filters)` | `transactions id ID` | All claims for a transaction ID |
| `by_census_code(db, code, year=...)` | `DATASET census-code CODE --year YEAR` | Matches in a supported census namespace |
| `search(db, name, field=..., ...)` | `DATASET search NAME` | Name/text matches, optionally ranked by edit distance |
| `entities(db, ...)` | `DATASET entities` | Matched records from a typed reference's register |
| `references(db, ...)` | `DATASET references` | Organization source rows, resolved targets and unresolved outcomes |
| `reference_types(db, ...)` | `DATASET types` | Observed organization reference types and counts |
| `eci_codes(db, level=..., ...)` | `DATASET eci-codes --level LEVEL` | Reported constituency LGD-to-ECI mappings and ambiguity flags |

The [dataset page](datasets/README.md) lists supported operations, primary
lookup, search fields and filters. A lookup code need not identify one row.
Helpers preserve published variants and duplicates; they do not normalize old
exports or infer missing relationships on read.

## Connections and dependencies

Helpers return native DuckDB relations over views named after their datasets.
They do not download files or own connections. Prepare a query to keep execution
options and input dependencies together:

```python
from lgd_query import load_release, connect, queries

query = queries.prepare("state_org_units", "search", "Post",
                        state_code="32", include_entity_name=True)
print(query.required_datasets)  # state_org_units and org_unit_details
release = load_release()
inputs = query.sources(release)
print([(d.name, d.observed_on, d.status) for d in inputs])
with connect(inputs, cache_dir="./data") as db:
    rows = query.execute(db).fetchall()
```

`prepare(dataset, operation, *args, **options)` accepts the helper's arguments
without `db`. It validates arguments and captures bound SQL without I/O or
importing DuckDB. The immutable result exposes `dataset`, `operation`,
`required_datasets` and expected `columns`; DuckDB checks actual input schemas
when `execute(db)` runs.

Direct helpers remain available. `queries.required_datasets(dataset, ...)`
inspects dependencies; `queries.sources(release, dataset, ...)` resolves them.
Pass the same lookup/enrichment options to the dependency helper and query.
The CLI handles these inputs automatically.

A pinned generation can contain different observation dates. A supplied
`observed_on` guard applies to every input; it does not reconstruct a historical
snapshot. Required but unavailable datasets fail explicitly. Inspect dates before
interpreting a missing reference or joining reports.

## Identifiers, filters and matching

All supplied filters combine with AND before ranking and limits. `None` leaves
a filter unused; use `is_null` for an SQL NULL predicate. Per-dataset pages group
filters by value type:

| Value type | Interpretation |
| --- | --- |
| Code | Nonnegative integer or ASCII digit string; string leading zeros are preserved, never inferred |
| Signed code | Signed integer or integer text; supplied sentinels are allowed only for documented fields |
| Text | Exact source spelling, including whitespace; numeric-looking values such as pincodes and organization-specific codes stay text |
| Integer | Nonnegative integer, for version fields |
| Date | ISO `YYYY-MM-DD` string or `datetime.date` |

LGD, census and ECI codes are different namespaces. Use only documented census
years. `changes` and `constituency_coverage` require `entity_type` when selecting
`entity_code`; other polymorphic codes should be scoped explicitly when a
particular namespace is intended.

`is_null="coverage_type"` and `is_blank="village_code"` also accept sequences of
columns. Blank means exactly `''`, distinct from NULL and whitespace-only text.
Column names are validated; blank predicates require text columns. Event
`since`/`until` bounds are inclusive and describe event dates, not collection coverage.

Search supports `exact`, `prefix`, `contains` (default) and `fuzzy`. It trims
outer whitespace, normalizes Unicode to NFC and lowercases. It does not
transliterate or remove accents; `%`, `_` and quotes are literal characters.
Missing names do not match. Fuzzy mode adds `distance`, defaults to
`max_distance=2`, and accepts `levenshtein` or `damerau_levenshtein`.
Distances count UTF-8 bytes, not Unicode characters. Search defaults to 20 results
(`limit=None` removes that bound); Python list/code helpers are unbounded.
Results sort by name and code/scope, with fuzzy distance first.

Lookup searches join documented codes, never names. They add `lookup_names`
with every distinct resolved label; ambiguous labels do not multiply source
rows. Fuzzy lookup distance is the best matching label. A resolved label does
not prove that the relationship is correct or valid on another date.

## Typed entity references

[Constituency coverage](datasets/constituency_coverage.md#follow-entity-codes-to-their-registers)
and the [organization cookbook](ORGANIZATION_QUERIES.md) document type namespaces,
input registers and result columns. Organization location and geographic
coverage are different references. Use `types` to inspect source values before
resolving them; use `references` when unresolved source rows matter.

Office queries can add reported location names with `include_entity_name=True`.
`entity_names` retains alternatives; `entity_name` is populated only for a unique
label. `entity_name_status` distinguishes matched, missing and ambiguous labels.
Name/status filters imply enrichment and apply before search limits. See
[name outcomes](ORGANIZATION_QUERIES.md#filter-reported-location-name-outcomes).

## Reported LGD-to-ECI constituency codes

[PRI](datasets/constituencies_mapping_pri.md#eci-code-lookup) and
[urban](datasets/constituencies_mapping_urban.md#eci-code-lookup) mapping reports
support `eci_codes(level="assembly"|"parliament", constituency_code=...,
state_code=..., eci_code=...)`. Filters combine; results preserve reported
alternatives and flag conflicting/reused ECI values. These are source claims,
not a verified electoral crosswalk. Blank/zero identifiers do not produce lookup rows.

## CLI

```sh
lgd-query villages search Rampur --state-code 9 --format json --provenance
lgd-query constituency_coverage list --is-null coverage_type --all
lgd-query state_org_units search Post --include-entity-name --state-code 32
lgd-query query 'SELECT * FROM districts WHERE state_code = ?' --datasets districts --params '["32"]'
```

| Option | Use |
| --- | --- |
| `--format json` | Machine-readable output; tables use Rich by default |
| `--limit N`, `--all` | Override the dataset CLI's 20-row preview |
| `--columns COL ...` | Select output columns in order |
| `--provenance` | Include generation and participating source metadata in JSON |
| `--cache-dir DIR` | Reuse verified local Parquet files; otherwise query remote ranges |
| `--observed-on DATE` | Require an exact source date for every participating input |
| `--is-null COL`, `--is-blank COL` | Missing-value predicates; repeat for several columns |
| `--field`, `--mode`, `--max-distance`, `--metric` | Select a search field and matching behavior |
| `--metadata-url URL` | Select an immutable generation or mirror; put this before the command |

Dataset filters use hyphens: `state_code` becomes `--state-code`. Use each
command's `--help` for supported options. `python -m lgd_query` is equivalent
to the installed command. All commands resolve discovery metadata once.

JSON query results contain `columns` and `rows`; previews also report `limit`
and `truncated`. Tables show participating report dates and update status.
`--provenance` adds source dates, status/reasons, file URLs/checksums and event
coverage. An update failure can leave an older file available.

Free-form SQL is unbounded by default. Its `--limit` limits displayed output,
not SQL execution. Duplicate result column names survive unless `--columns`
requires disambiguation; give them aliases in SQL. Use bound `--params` values
for user-supplied search terms rather than interpolating SQL.

Output streams in batches of at most 1,000 rows. Dates become JSON strings;
non-finite floats become `"NaN"`, `"Infinity"` or `"-Infinity"`; SQL NULL is JSON
null. Non-string-key maps use parallel `key`/`value` arrays; string-key maps use
objects. Errors exit nonzero. Dataset arguments and parameter JSON are checked
before network access; raw SQL/result-schema errors require execution.
