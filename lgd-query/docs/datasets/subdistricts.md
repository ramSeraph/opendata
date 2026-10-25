# subdistricts

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/subdistricts.md) · [API/CLI conventions](../QUERIES.md)

LGD's subdistrict register, with English names, versions, district and
state references, and 2001/2011 census identifiers. Each row identifies
one subdistrict by `subdistrict_code`; its version and administrative
parents are attributes.

Parent codes connect to [districts](districts.md) and [states](states.md),
while their supplied names support lookups without those joins. A
subdistrict and a development block have separate LGD identifiers;
[blocks](blocks.md) describes the latter.

## API

- `by_code(db, code)` selects `subdistrict_code`.
- `by_census_code(db, code, year=...)` supports 2001 and 2011.
- `list` and `search` return all supplied columns; only the `subdistricts` view is required.
- Filters: `state_code` and `district_code` on list/search/census lookup; both must match. No local-name field.

## CLI

```sh
lgd-query subdistricts list --state-code 32 --district-code 559
```
