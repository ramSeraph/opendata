# subdistricts

LGD's subdistrict register, with English names, versions, district and
state references, and 2001/2011 census identifiers. Each row identifies
one subdistrict by `subdistrict_code`; its version and administrative
parents are attributes.

Parent codes connect to [districts](districts.md) and [states](states.md),
while their supplied names support lookups without those joins. A
subdistrict and a development block have separate LGD identifiers;
[blocks](blocks.md) describes the latter.

```python
from lgd_query.queries import subdistricts

rows = subdistricts.list(db).fetchall()
matches = subdistricts.search(db, "name", mode="fuzzy", max_distance=2).fetchall()
```

`list`, `by_code`, `by_census_code(year=2001|2011)` and `search` return all
supplied columns. `by_code` selects `subdistrict_code`. List and search filters: `state_code`, `district_code`.
District/subdistrict census lookups also accept their parent filters. Census
codes are distinct from LGD codes and are not assumed globally unique.

Only the `subdistricts` view is required. Parent names remain as supplied in this
report. No implicit hierarchy join is needed. Lists/lookups are ordered by
name and scope/code; fuzzy results sort by distance first.

Search supports exact/prefix/contains/fuzzy matching, `limit=20` (or `None`),
`max_distance=2`, and `metric="levenshtein"|"damerau_levenshtein"`.

This report has no local-name column. Both supplied parent filters, where available, must match.

CLI: `lgd-query subdistricts list`, `code CODE`, `census-code CODE --year YEAR`,
and `search NAME`. Use `--help` on a command for its options.
Dataset commands preview 20 rows; use `--limit N`, `--all` and `--columns`
to control output. See [shared CLI options](../QUERIES.md#cli) for missing-value
filters and source provenance.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/subdistricts.md) and [shared query rules](../QUERIES.md).
