# lgd-query

A small Python client for the public [LGD Parquet releases](https://github.com/ramSeraph/opendata/releases/tag/lgd-parquet-latest).
It has three public APIs: metadata resolution, verified downloading and DuckDB
access. The CLI uses those same APIs. No GitHub account or API server is needed.

This directory is a standalone distribution. Its wheel contains only
`lgd_query`; it has no dependency on the repository's scrapers, converters or
history code. Python 3.11+ is required, matching DuckDB 2's minimum. Metadata and downloads use the standard
library; SQL access additionally requires DuckDB 2 or newer.
Rich is an optional dependency for CLI tables.

## Installation

Until the first PyPI release, install from this directory:

```sh
pip install .                 # Metadata API, download API and their CLI commands
pip install '.[duckdb]'       # Also include DuckDB querying
pip install '.[cli,duckdb]'    # All APIs and Rich table output
```

The distribution name is `lgd-query`; the Python import is `lgd_query`.
After publication, the corresponding installs are `pip install lgd-query` and
`pip install 'lgd-query[duckdb]'`.

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
are controlled by DuckDB. No domain-specific query helpers are included yet.

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
```

All commands default to Rich tables. Use `--format json` for scriptable output;
JSON mode does not require Rich. Resolved metadata tables summarize the dataset
and optional schema; JSON retains all manifest/source details. SQL JSON results
have `columns` and `rows` arrays, preserving duplicate column names. Both formats
use batches of at most 1,000 query rows; tables repeat their headers per batch.
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

## Development and packaging

```sh
pip install -e '.[cli,duckdb]'
python -m unittest discover -s tests -v
uv build --out-dir dist
```

Build from this directory. Package discovery is restricted to `src/lgd_query`;
the rest of the repository is outside the distribution. Tests use synthetic
release metadata and small generated Parquet files. Tests that require DuckDB
are skipped when the optional dependency is absent.

## Version releases

The repository workflow is `.github/workflows/lgd-query-publish.yml`, matching
the PyPI trusted-publisher configuration. It uses the `pypi` GitHub environment
and [OIDC trusted publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

A pushed `lgd-query-v<version>` tag builds this directory, checks that the tag
matches `pyproject.toml`, validates the distribution contents and PyPI metadata,
and tests the built wheel on Python 3.11 and 3.14. Only after these checks pass
does it upload the same wheel/source archive to PyPI and create a corresponding
GitHub release with those files attached. No scraper or history files are bundled.

For example, after committing version `0.1.0`:

```sh
git tag lgd-query-v0.1.0
git push origin lgd-query-v0.1.0
```

Manual workflow runs on a branch only build/test. A manual run on a matching
version tag also publishes. Failed publication jobs can be retried using the
same built artifacts. GitHub release titles and tags use the library prefix to
keep package versions separate from the data releases.

Before a retry uploads files, the workflow compares any existing PyPI files with
the checked local sizes and SHA-256 hashes. Different bytes under the same version
stop publication. Before creating/updating the GitHub release, it verifies that
both files match PyPI. If PyPI's metadata has not caught up yet, retry that job;
it will not attach unconfirmed files. For a partial upload, rerun failed jobs
with the original build artifacts instead of rebuilding the same version.
