# states

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/states.md) · [API/CLI conventions](../QUERIES.md)

LGD's register of states and union territories, with English and local
names, the reported state/UT classification, version and 2001/2011 census
identifiers. Each row identifies one state or union territory by
`state_code`.

Use this register to resolve state references in other datasets.
`state_or_ut` retains LGD's classification, and census identifiers remain
separate from LGD codes. Optional local names may be absent.

## API

- `by_code(db, code)` selects `state_code`.
- `by_census_code(db, code, year=...)` supports 2001 and 2011.
- `list` and `search` return all supplied columns; only the `states` view is required.
- Filters: `kind="state"|"ut"` on list/search; `field="english"|"local"` on search.

## CLI

```sh
lgd-query states search kerla --mode fuzzy
```
