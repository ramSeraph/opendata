# assembly_constituencies

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/assembly_constituencies.md) · [API/CLI conventions](../QUERIES.md)

LGD's assembly-constituency register supplies an assembly's code
and name together with parliamentary-constituency and state references.
`assembly_constituency_code` identifies the row; the parliamentary
parent and state are attributes. Parliamentary-only placeholders
with no assembly code or name are omitted.

Reported LGD-to-ECI mappings are available through the
[urban](constituencies_mapping_urban.md#eci-code-lookup)
and [historical PRI](constituencies_mapping_pri.md#eci-code-lookup) query helpers;
inspect their source dates and ambiguity flags.

## API

- `by_code(db, code, **filters)` selects `assembly_constituency_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `assembly_constituency_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `assembly_constituency_name` | Supplied `assembly_constituency_name` | None |
| `parliament_constituency_name` | Supplied `parliament_constituency_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `assembly_constituency_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `assembly_constituency_code`, `parliament_constituency_code`, `state_code` |
| Text | `assembly_constituency_name`, `parliament_constituency_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query assembly_constituencies code 3677
```
