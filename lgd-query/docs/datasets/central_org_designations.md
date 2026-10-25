# central_org_designations

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/central_org_designations.md) · [API/CLI conventions](../QUERIES.md)

This report lists designation titles within central organizations,
including English/local names and reported levels, such as postal
roles at different office levels. It describes titles rather than
named office-holders or individual office staffing.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

The normalized key is `(designation_code, organization_level_code, organization_level_name)`.
Organization remain attributes and optional filters.
`by_code` can return several level associations for one designation code;
use level filters to select an association. Blank level codes remain a source
limitation described in the [source schema](https://github.com/ramSeraph/opendata/blob/master/lgd/parquet/datasets/central_org_designations.md).

## API

- `by_code(db, code, **filters)` selects `designation_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `designation_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `designation_name` | Supplied `designation_name` | None |
| `designation_name_local` | Supplied `designation_name_local` | None |
| `organization_level_name` | Supplied `organization_level_name` | None |
| `organization_name` | Supplied `organization_name` | None |
| `english` | Supplied `designation_name` | None |
| `local` | Supplied `designation_name_local` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `designation_code`, `organization_level_code`, `organization_code` |
| Text | `designation_name`, `designation_name_local`, `organization_level_name`, `organization_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query central_org_designations list --limit 5
```
