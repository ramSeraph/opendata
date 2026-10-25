# state_admin_depts

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/state_admin_depts.md) · [API/CLI conventions](../QUERIES.md)

Despite its filename, this report defines administrative-unit
levels, not a directory of departments. It supplies level codes/names,
a parent administrative reference, state and optional source metadata
about hierarchy, publication and activity. The level code identifies
the record; state remains an attribute.

See the [organization data and source diagrams](../ORGANIZATION_DATA.md) for how this report relates to the others.

## API

- `by_code(db, code, **filters)` selects `administrative_unit_level_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `administrative_unit_level_name`.

The normalized key is `administrative_unit_level_code`. `state_code` remains an
optional filter and supplies context when comparing this report with other
datasets. It is not part of this dataset's row identity.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `administrative_unit_level_name` | Supplied `administrative_unit_level_name` | None |
| `administrative_unit_level_name_local` | Supplied `administrative_unit_level_name_local` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `administrative_unit_level_name` | None |
| `local` | Supplied `administrative_unit_level_name_local` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `administrative_unit_level_code`, `organization_level_code`, `parent_organization_level_code`, `state_code` |
| Text | `administrative_unit_level_name`, `administrative_unit_level_name_local`, `created_by`, `created_on`, `hierarchy`, `is_active`, `publication_status`, `local_body_level`, `organization_located_at_levels`, `overlap_unit`, `parent_category`, `revenue_entity`, `unit_level_type`, `state_name` |
| Signed code | `parent_administrative_code` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query state_admin_depts list --limit 5
```
