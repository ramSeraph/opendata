# Standalone LGD Parquet conversion

Convert one LGD report to one canonical Parquet file. This package owns source
schemas, header aliases, value validation, duplicate handling and Parquet writing.
It requires Python 3.12+ and DuckDB 2; it has no dependency on the history package,
PyArrow, Iceberg, a database file, GitHub or a catalog service.

From `lgd/`:

```sh
uv run --extra parquet python -m parquet states data/states.csv data/states.parquet
uv run --extra parquet python -m parquet villages data/villages.23Oct2026.csv.7z data/villages.parquet
uv run --extra parquet python -m parquet transactions data/transactions.csv.gz data/transactions.parquet
```

Install `7z` for archive inputs. Multi-report archives require an explicit member:

```sh
uv run --extra parquet python -m parquet states data/states.Jan2024.7z data/states.parquet \
  --member states.01Jan2024.csv
```

The selected CSV streams from `7z` through the CSV reader into DuckDB in bounded
batches (at most 8,192 rows or approximately 2 Mi characters, plus one record).
No intermediate CSV or gzip file is written. The original bytes are hashed as
they are read; the member size, CRC and extractor exit status must all pass
before writing the Parquet output.
The output is written to a temporary sibling and renamed after a successful
write. Rejected inputs leave an existing output untouched. Spill files are
cleaned up on both success and failure.

The default DuckDB limits are two threads, 512 MB memory and 2 GB spill space;
adjust `--threads`, `--memory-limit` and `--max-temp-size` for larger reports.
Allow space for the compressed input, DuckDB spill and Parquet output.
Conversion performs no downloads. Plain CSV and existing gzip CSV inputs use
the same streaming reader.

The [daily publishing workflow](PUBLISHING.md) discovers source reports in GitHub
Releases, runs this converter, and publishes dated Parquet files and metadata.

The command prints a JSON receipt containing input and decompressed CSV SHA-256
hashes, the selected archive member, supplied fields, source/output row counts,
collapsed rows and output size/hash. Constituency layout diagnostics identify
known missing prefix rows. The receipt describes the input that was converted;
successful conversion does not establish that LGD supplied a complete report.

## Schemas and interpretation

[One schema document per dataset](datasets/README.md) describes row identity,
canonical fields, stable field IDs, source headers and dataset-specific rules.
There are 37 snapshot-report schemas and two cumulative event-report schemas.
Only datasets with implemented, validated readers are listed.

Common rules:

- Codes, names, source flags and free text remain strings. Leading zeroes,
  Unicode, capitalization, whitespace and source sentinel strings are retained.
- A supplied blank text value remains `''`. An allowed but absent source column
  becomes `NULL`. Snapshot version columns are integers; a supplied empty version
  becomes `NULL`. Event dates and integer versions require lossless conversion.
- Header matching ignores case, whitespace, parentheses, periods and hyphens;
  additional spelling/layout aliases are explicit. Unknown, duplicate or missing
  required headers fail conversion.
- Snapshot readers other than organization-unit coverage discard serial numbers.
  Identical reported records collapse;
  versions differing only in a known integer version use the highest version.
  Conflicting attributes for the same record key fail conversion. Village
  categories and the documented association/ward variants remain separate rows.
- Event reports retain every row, including repeated or conflicting event claims.
  The legacy changes report keeps its source serial as `report_serial`.
- Organization-unit coverage also retains every source row, including repeated
  claims and units with no supplied coverage details; it has no stable claim ID.
- Parquet uses Zstandard compression and stable field IDs. IDs belong to a
  dataset and are independent of source column order. Shared concepts use the
  same field name and type across datasets.

The output contains the source fields listed in each schema document. It contains
only records supplied by that report: no inferred deletions, carried older rows,
observation ledger or validity intervals. Snapshot files do not embed a collection
date; retain the dated filename or the printed conversion receipt alongside them.
The separate history layer imports these same parsers to build dated histories
and Iceberg exports.

```sql
SELECT state_code, state_name
FROM read_parquet('data/states.parquet');
```

## Validation

```sh
uv run --extra parquet python -m unittest tests.test_parquet
```

Tests cover all 39 schemas, value/type/field-ID preservation, duplicate policies,
missing fields, archive checks, atomic output and a CLI run with history,
PyArrow and Iceberg imports blocked.
