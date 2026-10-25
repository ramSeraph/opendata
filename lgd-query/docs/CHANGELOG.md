# Changelog

## 0.2.0 — 25 October 2026

This release adds the **experimental dataset-aware query API** and corresponding
CLI commands. Arguments, result columns, lookup rules and interpretations of
dataset relationships may change between releases. Metadata resolution, verified
downloads and general DuckDB access remain separate reader interfaces.

- Query helpers for all 39 datasets: identifier lookups, name searches,
  report-specific filters and documented joins for missing names.
- Constituency ECI-code lookups and organization location/coverage reference
  resolution, preserving ambiguous matches and unresolved source claims.
- `queries.prepare()` to validate a query and identify its input datasets before
  resolving release metadata or opening DuckDB.
- Explicit Python signatures and packaged type stubs, consistent `code=`
  arguments, and filters that distinguish NULL from blank strings.
- Dataset CLI commands preview 20 rows by default, with `--limit`, `--all`,
  `--columns` and optional JSON provenance. Free-form SQL keeps its unbounded
  default. Query tables show participating report dates and update status.
- Organization `types` and `references` commands, missing/ambiguous location-name
  filters, and dependency selection scoped to state or central reports.
- Per-dataset API guides and expanded organization diagrams and explanations.

Helper availability does not imply that a dataset is present in every release
generation. NOFN collection remains retired; its helpers support historical
Parquet input.

## 0.1.0 — 23 October 2026

- Initial standalone metadata, checksum-verified download and DuckDB APIs.
- JSON/Rich CLI for release discovery, downloading and free-form SQL.
- Remote Parquet queries and configurable local caching, with no dependency on
  the repository's scraper, converter or history code.
