# districts

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/districts.md) · [API/CLI conventions](../QUERIES.md)

LGD's district register: one district per `district_code`, with its
English name, state code/name and 2001/2011 census identifiers. State is
a reported parent attribute, so a changed state reference updates the
district rather than creating a different district identity.

State names are already supplied for ordinary lookups. Use `state_code`
to connect to [states](states.md); labels may differ between reports.
District census codes belong to a different namespace from LGD codes.

## API

- `by_code(db, code)` selects `district_code`.
- `by_census_code(db, code, year=...)` supports 2001 and 2011.
- `list` and `search` return all supplied columns; only the `districts` view is required.
- Filters: `state_code` on list/search/census lookup. No local-name field.

## CLI

```sh
lgd-query districts list --state-code 32
```
