# central_orgs

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/central_orgs.md) · [API/CLI conventions](../QUERIES.md)

This directory identifies central departments and organizations by
`organization_code`, with names, types and reported parent
organizations. It has no state columns. A parent ministry or
organization can appear only as a reference; conversion does not
synthesize a missing parent row.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

- `by_code(db, code, **filters)` selects `organization_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `organization_name` | Supplied `organization_name` | None |
| `parent_organization_name` | Supplied `parent_organization_name` | None |
| `english` | Supplied `organization_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `organization_code`, `parent_organization_code` |
| Text | `organization_name`, `organization_type`, `parent_organization_name`, `parent_organization_type` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query central_orgs search Posts
```
