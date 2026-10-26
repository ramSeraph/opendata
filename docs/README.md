# GitHub Pages website

The site provides direct navigation and access to collected government data.
Use descriptive page titles, compact navigation, and source information; keep
introductory copy brief and avoid promotional headings or feature banners.

The authored site lives in `docs/`. The deployment uploads the separate
`.pages-build/` directory assembled by `tools/build_pages.py`; generated Parquets
and organization bundles are never committed into the website source tree.

## Build and preview

From the repository root:

```sh
uv run --no-project --python 3.12 --with duckdb==2.0.0 python tools/build_pages.py
python3 tools/serve_pages.py --directory .pages-build
```

Open `http://localhost:8030/opendata/`. The preview uses the same project path
as GitHub Pages and permits cross-origin reads of its static files.
Use `--output <empty-directory>` for another build. Downloads are cached in
`lgd/data/pages-cache` and reverified before reuse. `--metadata <saved-index.json>`
pins a specific upstream index for a reproducible build. The output directory
must be separate from `docs/` and empty to avoid publishing obsolete data files.

The existing workflow collects the raw archive listings and Wikidata reports
before building. For a complete local preview, collect those ancillary files as
shown in `.github/workflows/docs.yml`; they remain ignored in `docs/`.

## Public data access

The build resolves one published Parquet index, verifies the size and SHA-256 of
every available Parquet and source manifest, and copies **all** available datasets
to `lgd/data/`. Unavailable datasets remain visible in the catalogue without
invented files or download links.

- `/opendata/lgd/datasets/` — searchable catalogue and direct download links.
- `/opendata/lgd/data/metadata.json` — current machine-readable index.
- `/opendata/lgd/data/<dataset>.<content-hash>.parquet` — the actual data.
- `/opendata/lgd/data/<dataset>.<content-hash>.json` — its schema and provenance.
- `/opendata/lgd/organizations/` — Centre/state organization explorer.

All public index references to Parquet files and manifests are rewritten to
their **GitHub Pages URLs**, including references inside the manifests; manifest
checksums are recalculated. The index remains compatible with `lgd-query`:

```python
from lgd_query import load_release, download

release = load_release(
    "https://ramseraph.github.io/opendata/lgd/data/metadata.json"
)
states = download(release.dataset("states"), "./data")
```

Other webpages can use `fetch()` against the same index and file URLs. GitHub
Pages supplies `Access-Control-Allow-Origin: *`; the original release asset
URLs are not used for these downloads. Source archive URLs may still appear
in provenance and on the separate original-archives page.

Read the current index before fetching files. Content hashes identify bytes,
but the Pages artifact retains only the current build's files, not a historical
archive. A cached older index may point to files removed by a later deployment.
Each report retains its actual source date and publication outcome; an available
older file is not presented as newly observed after an update failure.

## Organization explorer

The web build reads the 14 required organization and geographic-reference inputs
from the same verified Parquets copied to the site. It derives one compressed
bundle per government and loads only the selected bundle. Centre loads lazily
too. The page shell does not embed the whole graph or require a browser Parquet
runtime. The raw files remain separately downloadable.

The offline builder under `lgd/visualizations/central_orgs/` continues to accept
local current-history projections. The Pages build instead uses the latest
**published report snapshots**, without carrying forward omitted rows from
local history. Counts can therefore differ from that offline projection.

For example, the 25 October 2026 source CSVs and published Parquets have blank
`organization_level_code` in every central and state designation row. Level
names and organization codes are still present. The daily explorer lists those
titles under their organizations, but cannot join them to units on organization
and level code. The local history projection can still contain older coded
associations that are absent from the daily snapshot. A zero match count in the
daily view does not establish that an office has no designations or staff.

The SQLRooms history prototype remains local in `lgd/data/villages-explorer/`.
Its Pages port is deferred; the history files it requires are not part of this
build.

## Workflow order and checks

The existing scraping workflow now calls the Parquet publisher after its source
listing is complete, then calls the existing Pages workflow. This replaces the
publisher's former `workflow_run` trigger, which could only start after the
embedded Pages job had already finished. Its manual and scheduled triggers are
retained. The Pages job waits for the publication attempt and can still show
older available files with their actual dates after partial publication failure.
The workflow template and generated daily workflow must remain in sync.

Checks:

```sh
node --test lgd/visualizations/central_orgs/model.test.cjs
uv run --no-project --with duckdb==2.0.0 python -m unittest discover -s tools -p 'test_pages_build.py'
```

With the local server and a test Chrome debugging endpoint on port 9231 running:

```sh
node tools/check_pages.mjs
```

The browser check covers responsive pages, dataset filtering, binary and
cross-origin downloads, archive selection, source descriptions, government
switching, title associations, large branches, and fuzzy search. The test
uses a raw data document for its cross-origin check so the catalogue's self-only
CSP does not mask the server's CORS behavior.
