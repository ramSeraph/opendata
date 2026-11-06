# Daily Parquet releases

[LGD Daily Parquet](../../.github/workflows/lgd_parquet.yml) converts the latest
available source reports using the standalone converter. It runs after **LGD
Daily Run** finishes, including partial failures, at 01:45 UTC daily as a
fallback, and on manual dispatch. It becomes automatic when the workflow is
merged into the default branch. There is no separate activation variable.

The workflow uses existing GitHub release inputs. It does not scrape LGD,
update historical tables, create Iceberg metadata, or make Git commits.
The converter itself has no workflow or GitHub dependency; release coordination
lives in [parquet_workflow.py](../utils/parquet_workflow.py) and
[parquet_release.py](../utils/parquet_release.py).

## Published files

The stable entry point is:

```text
https://github.com/ramSeraph/opendata/releases/download/lgd-parquet-latest/metadata.json
```

Create the public `lgd-parquet-latest` release manually before the first run.
The workflow uploads assets to existing releases; it never creates releases or
tags. Preparation checks the destinations before starting conversion jobs.
Files use names such as `villages.2026-10-23.<revision>.parquet`. The revision
identifies the pinned source assets and converter/publisher versions. Each file
has a companion JSON manifest with the source URLs and checksums, canonical
schema, row counts, converter commit, and conversion diagnostics.

The long-lived `lgd-parquet-latest` release keeps only the latest successfully
published export for each dataset, its manifest, any referenced discrepancy
evidence, and the current discovery metadata. After publishing and verifying
the new index, the workflow removes superseded exports and old indexes.
A failed dataset keeps its last successful export. Existing supplementary
`lgd-parquet-extra-0001` releases are included in cleanup if present.

Versioned URLs identify fixed contents while those files are current; old URLs
expire after replacement. Read `metadata.json` again to discover the current
files. Raw CSV archives in `lgd-latest*` and `lgd-archive*` are never removed by
this publisher. Those archives remain the source for rebuilding history.
Capacity planning reserves room under GitHub's [1,000 assets per release and
2 GiB per asset limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas).

`metadata.json` lists each dataset's `daily.file` URL, size and SHA-256,
`daily.rows`, actual `daily.observed_on` date, manifest, and update outcome.
Dates can differ between datasets; the publication timestamp is separate.
A later report with identical values still advances the observation date.
Retries of the same input and converter reuse already uploaded files.

`changes` and `transactions` remain cumulative event files. Their undated input
names do not establish a collection date, so `observed_on` is null. Their asset
names use the source upload date, identified separately as `uploaded_at`.
`coverage` gives the first/last reported event dates and the actual dates in the
paired collection ledger. The publisher verifies that every reported event date
belongs to that ledger; gaps and dates without events are not filled in.

These are report snapshots, not effective historical state. Incomplete source
reports retain the standalone converter's documented semantics. An omitted row
does not establish a deletion; historical carry-forward is separate work.

## Reading with DuckDB

Fetch the metadata once and query its versioned file URLs. If an update replaces
those files before the query finishes, fetch metadata again. Public readers need
no GitHub token or catalog server:

```python
import json
from urllib.request import urlopen
import duckdb

url = ('https://github.com/ramSeraph/opendata/releases/download/'
       'lgd-parquet-latest/metadata.json')
with urlopen(url) as response:
    metadata = json.load(response)
entry = metadata['datasets']['villages']
print(entry['daily']['observed_on'], entry['outcome'])
rows = duckdb.sql('SELECT * FROM read_parquet(?) LIMIT 10',
                 params=[entry['daily']['file']['url']]).fetchall()
```

An unavailable dataset may have no `daily` reference until its first successful
conversion. The [schema documents](datasets/README.md) explain individual fields.

## Coordination, failures and retries

Preparation uses only Python's standard library and the GitHub CLI. It inventories
`lgd-latest` and its supplementary releases, pins inputs and code, verifies
previous exports, and excludes unchanged datasets before any converter setup.
Monthly raw archives are outside this daily publication workflow.

Matrix conversion jobs have no parallelism cap. Each job has a four-hour limit
and a 225-minute conversion/upload step. They install only DuckDB 2.0.0 and the
7z reader; neither scraper dependencies nor history/Iceberg packages are needed.
The input streams into bounded CSV batches with no intermediate gzip file.
DuckDB uses two threads, a 1 GB memory limit and a 2 GB spill limit. Successful
workers upload their Parquet and manifest directly to Releases. Only the small
pinned plan passes through an Actions artifact.

A failed conversion or upload preserves the previous published file and its
actual date. Other datasets can advance. The coordinator records `updated`,
`unchanged`, `unavailable`, `blocked` or `failed` per dataset. Blocked/failed
selected datasets cause a failed workflow even after successful results have
been published. An absent daily source is an `unavailable` outcome, not an empty
replacement or inferred deletion.

One final job updates metadata under the publication concurrency lock. It checks
the manifests and their files, uploads a versioned index, temporarily saves the
previous index as `metadata.previous.json`, and replaces `metadata.json` last.
GitHub replacement is delete/upload, so a short discovery gap is possible;
readers can retry or use the temporary previous copy. Only after verifying the
new publication does cleanup remove superseded files and that previous copy.
The current versioned index remains available for recovery. Cleanup checks every
current manifest, data file and evidence file before deleting anything; a cleanup
failure leaves the current publication readable and can be retried.

Use **Re-run failed jobs** to reuse the pinned plan; workers check for completed
uploads before installing dependencies. If an earlier attempt already published
partial results, newly completed datasets are added through a new versioned
index, then superseded files are removed. A new dispatch rediscovers sources.
If a pinned raw asset was replaced or moved by archiving, use a new dispatch.

Manual dispatch defaults to `mode=update` with all 39 supported datasets. An
optional space-separated `datasets` input limits conversion. Use `mode=recover`
to restore `metadata.json` from the newest verified complete dated index without
reconverting reports. Recovery shares the same lock and checks referenced files.

Use `mode=prune` to clean up accumulated exports without converting or changing
the advertised dataset contents. It shares the publication lock and upgrades
older metadata to latest-only retention. To preview the exact asset names and
IDs locally, run `python -m utils.parquet_workflow prune`; the command writes
`data/parquet-publication/cleanup.json` and deletes nothing. Prefer the workflow
for applying cleanup. A local `prune --apply` must run only when no publisher is
active. Unknown filenames and releases outside the Parquet namespace are left
alone.

## Local verification

```sh
cd lgd
uv run --no-project --python 3.12 --with duckdb==2.0.0 \
  python -m unittest tests.test_parquet_workflow tests.test_parquet
python -m utils.parquet_workflow prepare --work data/parquet-publication-review
```

`prepare` reads release metadata and writes a local plan; it uploads nothing.
The tests simulate partial worker failure, source replacement, unchanged inputs,
same-day corrections, stale plans, release rollover, and interrupted discovery
replacement. They also run the real converter against a synthetic 7z report.
