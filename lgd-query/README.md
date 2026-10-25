# lgd-query

Query India's [Local Government Directory Parquet releases](https://github.com/ramSeraph/opendata/releases/tag/lgd-parquet-latest)
from Python or the command line. No account or API server is required.

The package provides three independent reader APIs: metadata resolution,
checksum-verified downloads, and DuckDB access. **Experimental dataset-aware
helpers** add code/name lookups and documented relationships across all 39 datasets.
Their arguments, output columns and interpretation of relationships may change.

## Install

```sh
pip install 'lgd-query[cli,duckdb]'
```

Python 3.11+ is required. The base `lgd-query` install supports metadata,
downloads and JSON output without third-party dependencies. The `duckdb` extra
adds DuckDB 2+; `cli` adds Rich tables. Dataset helpers are available from 0.2.0.

## Use the CLI

```sh
# Discover available datasets and their actual report dates.
lgd-query list --available-only

# Search names or look up an LGD code.
lgd-query states search kerla --mode fuzzy
lgd-query districts list --state-code 32
lgd-query villages code 626704 --format json --provenance

# Download verified Parquet files to a directory you choose.
lgd-query download states districts --directory ./data

# Run your own DuckDB SQL over selected datasets.
lgd-query query 'SELECT state_code, count(*) AS districts FROM districts GROUP BY state_code' --datasets districts
```

Dataset commands preview 20 rows. Use `--limit N`, `--all`, or `--columns` to
control output; use `--format json` for scripts. Add `--cache-dir ./data` to
queries to reuse checksum-verified local files. Otherwise DuckDB reads remote
Parquet ranges. `lgd-query DATASET COMMAND --help` lists supported filters.

## Use Python

```python
from lgd_query import load_release, download, connect

release = load_release()                  # Pin one metadata generation.
source = release.dataset("districts")
print(source.observed_on, source.status)
path = download(source, directory="./data")

with connect([source], cache_dir="./data") as db:
    rows = db.sql("SELECT * FROM districts WHERE state_code = ?", params=["32"]).fetchall()
```

For dataset-aware queries, preparation keeps the query and its dependencies together:

```python
from lgd_query import queries

query = queries.prepare("state_org_units", "search", "Post",
                        state_code="32", include_entity_name=True)
with connect(query.sources(release), cache_dir="./data") as db:
    rows = query.execute(db).fetchall()
```

Helpers return native DuckDB relations. Direct calls such as
`queries.states.by_code(db, code="32")` work with views you have already opened.

## Choose a guide

| Task | Guide |
| --- | --- |
| Find a dataset, its key, fields and available queries | [Dataset index](docs/datasets/README.md) |
| Metadata, downloads, remote SQL and cache behavior | [Reader APIs](docs/READER.md) |
| Matching, filters, dependencies and CLI options | [Query guide](docs/QUERIES.md) |
| Understand organizations, offices, levels and coverage | [Organization data model](docs/ORGANIZATION_DATA.md) |
| Explore office locations and coverage claims | [Organization query cookbook](docs/ORGANIZATION_QUERIES.md) |
| See release changes | [Changelog](docs/CHANGELOG.md) |

A generation can contain reports from different dates. Missing data does not
establish deletion; mapping rows need not represent unique entities.
`--observed-on` checks the exact source date—it does not retrieve historical
snapshots. Inspect the dataset's schema and report dates before interpreting joins.

## Development

```sh
pip install -e '.[cli,duckdb]'
python -m unittest discover -s tests
PYTHONPATH=src python tools/generate_query_stubs.py --check
uv build --out-dir dist
```

Only `lgd_query` is packaged; scraper, converter and history code are separate.
Maintainers: [release procedure](docs/RELEASING.md).
