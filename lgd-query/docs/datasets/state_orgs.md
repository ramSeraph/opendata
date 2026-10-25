# state_orgs

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/state_orgs.md) · [API/CLI conventions](../QUERIES.md)

This directory identifies state departments and organizations by
`organization_code`, with names, organization type, state and reported
parent organization. State is an attribute. The parent may appear
only as a reference, so the directory need not contain a row for every
parent in the hierarchy.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

- `by_code(db, code, **filters)` selects `organization_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `organization_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `organization_name` | Supplied `organization_name` | None |
| `parent_organization_name` | Supplied `parent_organization_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `organization_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `organization_code`, `parent_organization_code`, `state_code` |
| Text | `organization_name`, `organization_type`, `parent_organization_name`, `parent_organization_type`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query state_orgs search Revenue --state-code 32
```
