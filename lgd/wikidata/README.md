# LGD / Wikidata sync checks

Compare Wikidata entities with the latest Local Government Directory (LGD)
exports and write JSON reports. The checkers read Wikidata; suggested corrections
are published in the reports for manual review.

From this directory, with Python 3.12+, `uv`, `wget`, and `7z` installed:

```sh
bash steps.sh
```

This is the same entry point used by GitHub Actions. It downloads the LGD inputs,
fetches each Wikidata dataset once, runs the six checkers, and collects report
counts. The reports cover states, divisions, districts, subdivisions,
subdistricts, and district panchayats.

`uv run download.py state` downloads an individual dataset. Each `check_*.py`
script can also be run separately once its Wikidata and LGD inputs are present.
Report generation can look up missing labels and effective dates online.

Files in `data/*.jsonl` and `data/*.jsonl.parts/` allow interrupted downloads to
resume. Existing entity records are reused. The workflow's cache is scoped to
the day so an interrupted run can resume without carrying old entity data into
the next day's reports.

Reports go into `reports/`, with counts in `reports/status.json`. Publishing
reports is a separate step in `.github/workflows/lgd_wikidata_sync_check.yml`.

The code is organized around:

- `steps.sh`, `download.py`, `raw_wikidata.py`: orchestration, download roots,
  retries, and checkpoints.
- `constants.py`: state-specific classes and names, QIDs, and property IDs.
- `common.py`, `filters.py`, `suffixes.py`, `lev.py`: shared checks and name matching.
- `check_*.py`: entity-specific checks and suggested corrections.

The workflow installs its runtime dependencies from `pyproject.toml`.

Run the offline regression tests from this directory:

```sh
uv run python -m unittest discover -p 'test_*.py'
node --test test_report_rendering.cjs
```
