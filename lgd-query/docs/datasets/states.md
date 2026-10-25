# states

LGD's register of states and union territories, with English and local
names, the reported state/UT classification, version and 2001/2011 census
identifiers. Each row identifies one state or union territory by
`state_code`.

Use this register to resolve state references in other datasets.
`state_or_ut` retains LGD's classification, and census identifiers remain
separate from LGD codes. Optional local names may be absent.

```python
from lgd_query.queries import states

rows = states.list(db).fetchall()
matches = states.search(db, "name", mode="fuzzy", max_distance=2).fetchall()
```

`list`, `by_code`, `by_census_code(year=2001|2011)` and `search` return all
supplied columns. `by_code` selects `state_code`. List and search filters: `kind="state"|"ut"`.
District/subdistrict census lookups also accept their parent filters. Census
codes are distinct from LGD codes and are not assumed globally unique.

Only the `states` view is required. Parent names remain as supplied in this
report. No implicit hierarchy join is needed. Lists/lookups are ordered by
name and scope/code; fuzzy results sort by distance first.

Search supports exact/prefix/contains/fuzzy matching, `limit=20` (or `None`),
`max_distance=2`, and `metric="levenshtein"|"damerau_levenshtein"`.

States search also accepts `field="english"|"local"`. Missing local names do not match.

CLI: `lgd-query states list`, `code CODE`, `census-code CODE --year YEAR`,
and `search NAME`. Use `--help` on a command for its options.

See the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/states.md) and [shared query rules](../QUERIES.md).
