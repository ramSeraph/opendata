# Reader APIs

[Start here](../README.md) · [Dataset queries](QUERIES.md)

Resolve release metadata, download verified files, and open DuckDB views independently.
These APIs do not interpret dataset relationships.

## Metadata API

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

## Download API

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

## DuckDB API

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
