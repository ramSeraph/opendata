# districts

LGD's district register: one district per `district_code`, with its
English name, state code/name and 2001/2011 census identifiers. State is
a reported parent attribute, so a changed state reference updates the
district rather than creating a different district identity.

State names are already supplied for ordinary lookups. Use `state_code`
to connect to [states](states.md); labels may differ between reports.
District census codes belong to a different namespace from LGD codes.

```python
from lgd_query.queries import districts

rows = districts.list(db).fetchall()
matches = districts.search(db, "name", mode="fuzzy", max_distance=2).fetchall()
```

`list`, `by_code`, `by_census_code(year=2001|2011)` and `search` return all
supplied columns. `by_code` selects `district_code`. List and search filters: `state_code`.
District/subdistrict census lookups also accept their parent filters. Census
codes are distinct from LGD codes and are not assumed globally unique.

Only the `districts` view is required. Parent names remain as supplied in this
report. No implicit hierarchy join is needed. Lists/lookups are ordered by
name and scope/code; fuzzy results sort by distance first.

Search supports exact/prefix/contains/fuzzy matching, `limit=20` (or `None`),
`max_distance=2`, and `metric="levenshtein"|"damerau_levenshtein"`.

This report has no local-name column. Both supplied parent filters, where available, must match.

CLI: `lgd-query districts list`, `code CODE`, `census-code CODE --year YEAR`,
and `search NAME`. Use `--help` on a command for its options.
Dataset commands preview 20 rows; use `--limit N`, `--all` and `--columns`
to control output. See [shared CLI options](../QUERIES.md#cli) for missing-value
filters and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/districts.md) and [shared query rules](../QUERIES.md).
