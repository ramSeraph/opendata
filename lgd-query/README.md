# lgd-query

A small Python client for the public [LGD Parquet releases](https://github.com/ramSeraph/opendata/releases/tag/lgd-parquet-latest).
It provides metadata resolution, verified downloading and DuckDB access, with
experimental dataset-specific query helpers layered on top. The CLI uses those same APIs.
No GitHub account or API server is needed.

This directory is a standalone distribution. Its wheel contains only
`lgd_query`; it has no dependency on the repository's scrapers, converters or
history code. Python 3.11+ is required, matching DuckDB 2's minimum. Metadata and downloads use the standard
library; SQL access additionally requires DuckDB 2 or newer.
Rich is an optional dependency for CLI tables.

## Installation

Install the published reader from PyPI:

```sh
pip install lgd-query                  # Metadata, downloads and their JSON CLI
pip install 'lgd-query[duckdb]'         # Also include DuckDB querying
pip install 'lgd-query[cli,duckdb]'      # All APIs and Rich table output
```

The distribution name is `lgd-query`; the Python import is `lgd_query`.
For a development checkout, install from this directory with
`pip install '.[cli,duckdb]'`. See the [changelog](docs/CHANGELOG.md) for releases.

## 1. Metadata API

```python
from lgd_query import load_release, load_manifest

release = load_release()
villages = release.dataset("villages")

print(release.generation, release.published_at, release.immutable_url)
print(villages.observed_on, villages.rows, villages.status)
print(villages.parquet.url, villages.parquet.size, villages.parquet.sha256)

# Optional extra request for canonical schema and original-source provenance.
manifest = load_manifest(villages)
print(manifest["schema"])
```

`load_release()` fetches `metadata.json` once. Its `Release` object retains that
generation, and datasets refer directly to immutable files even if the latest
index changes. Accessing `release.datasets` or `release.dataset()` makes no
requests. New datasets can be discovered without updating a hardcoded registry.
`load_manifest()` verifies the manifest's size/hash and agreement with the index.

`release.datasets` is a read-only mapping including unavailable datasets. Each
`Dataset` exposes `name`, `available`, `status`, `reason`, `representation`,
`observed_on`, `uploaded_at`, `rows`, `parquet`, `manifest`, `identity`,
`coverage` and `metadata`. `parquet` and `manifest` are `Asset` references with
`url`, `size` and `sha256`. An unavailable dataset has no file references;
`release.dataset(name)` raises `DatasetUnavailableError` for it. An unknown name
raises `KeyError`.

“Latest” means the files advertised in one release index. Datasets can have
different source dates. A failed update can retain a usable older file, with its
actual date and failure status. Require an exact date when freshness matters:

```python
villages = release.dataset("villages", observed_on="2026-10-23")
```

A mismatch raises `ObservationDateError`; this is a freshness check, not a
historical lookup. Cumulative `changes` and `transactions` reports have
`observed_on=None`; their `coverage` describes event dates and collection coverage.
Publication/upload timestamps do not establish an observation date. These files
contain supplied report rows; omissions do not prove deletions.

To reopen a generation, pass its immutable URL to `load_release(url)`. For an
offline metadata lookup, save `release.metadata` as JSON and reopen it with
`Release.from_dict(document)`. `metadata` and `coverage` return detached copies.
Metadata requests accept `timeout=30` and `retries=2`. Transient HTTP responses,
including a brief 404 during index replacement, get bounded retries. The reader
does not silently fall back to `metadata.previous.json`; that URL can be supplied
explicitly if the preceding generation is wanted.

## 2. Download API

```python
from lgd_query import download

path = download(villages, directory="./data")
```

The returned `pathlib.Path` names a complete Parquet file whose size and SHA-256
match the resolved metadata. Files are named `<dataset>.<sha256>.parquet`, so
different contents coexist in the cache. Every reuse verifies the cached file.
A corrupt cached file is replaced only after its replacement verifies. Downloads
stream to unique temporary files and rename after verification; failures clean
up temporary files and never expose partial final files. No cache pruning occurs.

`download()` accepts `timeout=30` and `retries=2` for HTTP connection/response
retries. A failed transfer or checksum check raises an error; a subsequent call
can retry the download. It requires neither DuckDB nor another metadata request.

## 3. DuckDB API

```python
from lgd_query import connect

states = release.dataset("states")
districts = release.dataset("districts")

with connect([states, districts]) as db:
    rows = db.sql("""
        SELECT s.state_name, count(*) AS district_count
        FROM districts d JOIN states s USING (state_code)
        GROUP BY s.state_name ORDER BY s.state_name
    """).fetchall()
```

`connect()` returns a native `duckdb.DuckDBPyConnection`, with one view per
selected dataset using its canonical name. Close it or use a context manager.
Only the requested datasets are opened. Resolve them from one `Release` to pin
one publication generation; their actual observation dates can still differ.

By default DuckDB queries the resolved remote Parquet URLs with HTTP range
requests. Its `httpfs` extension may be installed automatically on first use.
Range queries do not verify the checksum of the entire file. For fully verified
files and reusable downloads:

```python
with connect([states, districts], cache_dir="./data") as db:
    rows = db.sql("SELECT * FROM districts WHERE state_code = ?", params=["33"]).fetchall()
```

With valid cached files and a saved index, this path works offline. DuckDB
settings can be supplied with `config={"threads": 2, "memory_limit": "512MB"}`.
`timeout` and `retries` affect cache downloads; remote range-request settings
are controlled by DuckDB.

## 4. Dataset query helpers (experimental)

The dataset-aware `lgd_query.queries` layer and its dataset-specific CLI commands
are **experimental**. Function arguments, result columns, lookup rules and
interpretations of dataset relationships may change between releases as our
understanding of LGD reports develops. This includes prepared queries and
organization reference resolution.

Helpers cover all 39 reports, starting with states, districts and subdistricts.
They are included starting with version 0.2.0. They run parameterized SQL on
an existing connection and return native
DuckDB relations. Helpers do not fetch metadata, download files or open
connections. Name searches with extra dependencies use documented code joins.

To declare a query and its dependencies together, use `queries.prepare`:

```python
from lgd_query import load_release, connect, queries

query = queries.prepare("state_org_units", "search", "Post",
                        state_code="32", include_entity_name=True)
release = load_release()
inputs = query.sources(release)
with connect(inputs, cache_dir="./data") as db:
    rows = query.execute(db).fetchall()
```

Preparation validates arguments and identifies required views without network
access or a DuckDB connection. The resulting query exposes `required_datasets`
and expected `columns`. Input resolution, downloads and connection ownership
remain explicit. You can also call the dataset helpers directly as below.

```python
from lgd_query import load_release, connect
from lgd_query.queries import states

release = load_release()
source = release.dataset("states")
print(source.observed_on, source.status)

with connect([source], cache_dir="./data") as db:
    rows = states.list(db).fetchall()
    territories = states.list(db, kind="ut").fetchall()
    kerala = states.by_code(db, "32").fetchall()
    census_matches = states.by_census_code(db, "32", year=2011).fetchall()
    matches = states.search(db, "kerla", mode="fuzzy", max_distance=2).fetchall()
```

| Helper | Behavior |
| --- | --- |
| `states.list(db, kind=None)` | All supplied rows; `"state"` selects `S`, `"ut"` selects `U`. |
| `states.by_code(db, code)` | Exact LGD code lookup; no census-code inference. |
| `states.by_census_code(db, code, year=...)` | All matches in the explicitly selected 2001 or 2011 census namespace. |
| `states.search(db, name, ...)` | Exact, literal prefix/substring, or fuzzy name search. |

Every result retains the report's seven columns: `state_code`, `state_version`,
`state_name`, `state_name_local`, `state_census_2001_code`,
`state_census_2011_code`, and `state_or_ut`. Codes remain strings; use string
arguments to retain any leading zeros. Missing matches give an empty relation.
Unfiltered lists retain unknown or missing classifications. Lists and lookups
are sorted by English name, then LGD code. Census codes are not assumed unique.

Search options are `mode="exact"|"prefix"|"contains"|"fuzzy"` (default
`"contains"`), `field="english"|"local"` (default `"english"`), `kind`, and
`limit` (default 20; `None` returns all matches). Comparisons trim surrounding
spaces, normalize Unicode to NFC and lowercase both inputs. Returned source text
is unchanged. `%` and `_` are literal characters. Missing or blank local names
do not match and do not fall back to English names.

Fuzzy search accepts `max_distance=2` and `metric="levenshtein"` or
`"damerau_levenshtein"`. It adds a `distance` column, applies the threshold, and
ranks by distance before name/code. These two options affect only fuzzy mode.
DuckDB's edit-distance functions count **UTF-8 bytes for non-ASCII text**:
their scores are not Unicode character/grapheme distances. For example, an
added Tamil character may count as three edits. Name normalization does not
remove accents or transliterate between scripts.

Consume results while the connection is open, using `.fetchall()` or other
DuckDB result methods; fully consume active results before reusing the same
connection. Relations also support further projection/filtering. The caller
retains the resolved `Dataset`, including its actual date and update status;
the helpers never silently refresh it. An exact freshness requirement can be
applied with `release.dataset("states", observed_on="YYYY-MM-DD")`.

### Districts

Districts already contain `state_code` and `state_name`. All four district
helpers need only the `districts` view, and preserve those supplied names even
when a separately loaded states report spells them differently. They do not
discard rows whose parent is absent from a states report.

```python
from lgd_query.queries import districts

source = release.dataset("districts")
with connect([source], cache_dir="./data") as db:
    kerala_districts = districts.list(db, state_code="32").fetchall()
    kollam = districts.by_code(db, "559").fetchall()
    census_matches = districts.by_census_code(
        db, "600", year=2011, state_code="32"
    ).fetchall()
    matches = districts.search(
        db, "kolam", state_code="32", mode="fuzzy", max_distance=2
    ).fetchall()
```

`districts.list(db, state_code=None)` returns all districts unless narrowed by
the supplied **LGD state code**. `districts.by_code(db, code)` looks up an LGD
district code. `districts.by_census_code(db, code, year=..., state_code=None)`
looks up all matching census codes for 2001 or 2011, optionally within one LGD
state. Census identifiers and names are not assumed unique across states;
helpers do not automatically choose one match or infer a state from its name.

`districts.search(db, name, state_code=None, ...)` has the same `mode`,
`max_distance`, `metric`, and `limit` options as states search. There is no
local-name field or state/UT classification in the district report, so district
helpers do not expose `field` or `kind`. State filtering and fuzzy thresholds
apply **before** the result limit. Ordering is by district name, state code and
district code, with fuzzy distance first in fuzzy mode.

Results preserve all six report columns: `district_code`, `district_name`,
`state_code`, `state_name`, `district_census_2001_code`, and
`district_census_2011_code`. Fuzzy results add `distance`.

### Subdistricts and the other datasets

All 39 reports have query helpers and CLI commands starting with version 0.2.0. See
the [dataset API index](https://github.com/ramSeraph/opendata/blob/master/lgd-query/docs/datasets/README.md)
and [shared query rules](https://github.com/ramSeraph/opendata/blob/master/lgd-query/docs/QUERIES.md)
for each report's identifiers, filters, search fields and name dependencies.

The [organization data diagrams](https://github.com/ramSeraph/opendata/blob/master/lgd-query/docs/ORGANIZATION_DATA.md)
show which datasets supply departments, offices, parent relationships, location,
coverage and designation titles, with examples from the released reports.

```python
from lgd_query.queries import subdistricts, villages

with connect([release.dataset("subdistricts")], cache_dir="./data") as db:
    rows = subdistricts.list(db, state_code="32", district_code="559").fetchall()
    rows = subdistricts.by_code(db, "5688").fetchall()

with connect([release.dataset("villages")], cache_dir="./data") as db:
    rows = villages.search(db, "Rampur", state_code="9").fetchall()
```

When names require another dataset, use `queries.sources` to resolve every
input from the same pinned release. The CLI loads these dependencies automatically.
Participating reports may have different dates; supplied names remain unchanged.

```python
from lgd_query import queries
from lgd_query.queries import constituencies_mapping_urban

inputs = queries.sources(release, "constituencies_mapping_urban", field="state_name")
print([(d.name, d.observed_on) for d in inputs])
with connect(inputs, cache_dir="./data") as db:
    rows = constituencies_mapping_urban.search(
        db, "Kerala", field="state_name", mode="exact"
    ).fetchall()
```

These helpers preserve associations, category/name variants and duplicate event
rows. They do not infer deletions, choose a unique entity from an ambiguous name,
or reconstruct historical snapshots from a current report.

Code lookups accept the same `code=` keyword across datasets; transactions use
`by_id(db, transaction_id=...)`. Runtime signatures and packaged type stubs
expose each report's accepted filters for help and editor completion. Use
`is_null="coverage_type"` or `is_blank="village_code"` to select missing values;
both also accept a sequence of column names. NULL, empty strings and whitespace
remain distinct, while an ordinary filter set to `None` remains unused.

## CLI

```sh
lgd-query list
lgd-query list --available-only
lgd-query list --format json
lgd-query resolve villages
lgd-query resolve villages --manifest --observed-on 2026-10-23
lgd-query download states districts --directory ./data
lgd-query query 'SELECT state_code, count(*) FROM districts GROUP BY state_code' --datasets districts
lgd-query query 'SELECT * FROM districts WHERE state_code = ?' --datasets districts --params '["33"]' --cache-dir ./data
lgd-query query 'SELECT count(*) FROM districts' --datasets districts --format json
lgd-query villages list --state-code 9 --limit 10 --columns village_code village_name
lgd-query constituency_coverage list --is-null coverage_type --all --format json
lgd-query state_org_units search Post --include-entity-name --provenance --format json
```

The experimental states helpers also have CLI commands:

```sh
lgd-query states list --kind ut
lgd-query states code 32 --format json
lgd-query states census-code 32 --year 2011
lgd-query states search kerla --mode fuzzy --max-distance 2 --cache-dir ./data
lgd-query states search delih --mode fuzzy --metric damerau_levenshtein
lgd-query states search தமிழ் --field local
```

Each states command accepts `--cache-dir`, `--observed-on`, and `--format`.
Search also accepts `--kind`, `--field`, `--limit`, `--mode`, `--max-distance`
and `--metric`. JSON uses the same `columns`/`rows` representation as raw SQL.
Only the states dataset is resolved and opened.

The district commands use the same structure:

```sh
lgd-query districts list --state-code 32
lgd-query districts code 559 --format json
lgd-query districts census-code 600 --year 2011 --state-code 32
lgd-query districts search kolam --state-code 32 --mode fuzzy --cache-dir ./data
```

They also accept `--cache-dir`, `--observed-on`, and `--format`. District `list`,
`census-code` and `search` accept `--state-code`; `search` accepts `--mode`,
`--max-distance`, `--metric` and `--limit`. Only the districts dataset is resolved
and opened, even when filtering by state.

All commands default to Rich tables. Use `--format json` for scriptable output;
JSON mode does not require Rich. Resolved metadata tables summarize the dataset
and optional schema; JSON retains all manifest/source details. SQL JSON results
have `columns` and `rows` arrays, preserving duplicate column names. Dataset
commands preview 20 rows by default; use `--limit N` or `--all`. Preview JSON
also has `limit` and `truncated`, and tables indicate when more matches exist.
`--columns` selects result fields. Free-form SQL retains its unbounded default,
with optional output controls; its SQL statement is executed as supplied.

Query tables show source dates and update status for all participating datasets.
`--provenance` adds the generation and per-input metadata to JSON. This exposes
retained older files and differing input dates. Missing-value CLI predicates
are `--is-null COLUMN` and `--is-blank COLUMN`, repeatable for several columns.
Invalid dataset query arguments, date guards and parameter JSON fail before
metadata requests or downloads.

Both formats use batches of at most 1,000 query rows; tables repeat their headers per batch.
Dates and other non-JSON scalar types are represented as strings. Non-finite
SQL floats use the JSON strings `"NaN"`, `"Infinity"` and `"-Infinity"`, including
inside lists and structs; SQL NULL remains JSON null. Errors exit
nonzero with a diagnostic.
Maps with non-string keys use parallel `key` and `value` arrays, matching
DuckDB's representation for complex map keys, so JSON object keys cannot
silently change their meaning. Maps with string keys remain JSON objects.
`python -m lgd_query` is equivalent to the installed `lgd-query` command.

Pass `--metadata-url URL` before the command to select an immutable generation
or mirror. `resolve`, `download` and `query` accept `--observed-on YYYY-MM-DD` to
require the exact report date. Every command fetches discovery metadata only once.

Organization exploration supports `types` to inspect observed reference types,
`references` to retain office/claim links and unresolved outcomes, and
`--entity-name-status` for missing or ambiguous office-location labels. See the
[organization guide](docs/ORGANIZATION_DATA.md#inspect-types-before-resolving-references).

## Development and packaging

```sh
pip install -e '.[cli,duckdb]'
python -m unittest discover -s tests -v
PYTHONPATH=src python tools/generate_query_stubs.py --check
uv build --out-dir dist
```

Build from this directory. Package discovery is restricted to `src/lgd_query`;
the rest of the repository is outside the distribution. Tests use synthetic
release metadata and small generated Parquet files. Tests that require DuckDB
are skipped when the optional dependency is absent.

Maintainers: see the [release guide](https://github.com/ramSeraph/opendata/blob/master/lgd-query/docs/RELEASING.md)
for version tags, trusted publishing and publication retries.
