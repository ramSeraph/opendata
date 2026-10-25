# parliament_constituencies

[All datasets](README.md) · [Schema and row identity](../../../lgd/parquet/datasets/parliament_constituencies.md) · [API/CLI conventions](../QUERIES.md)

LGD's parliamentary-constituency register supplies each
`parliament_constituency_code`, its name and state code/name. The LGD
constituency code identifies the row; state is an attribute.

Reported LGD-to-ECI mappings are available through the
[urban](constituencies_mapping_urban.md#eci-code-lookup)
and [historical PRI](constituencies_mapping_pri.md#eci-code-lookup) query helpers;
inspect their source dates and ambiguity flags.

## API

- `by_code(db, code, **filters)` selects `parliament_constituency_code` exactly and retains all matches.
- `search(db, name, field="english", **options)` defaults to `parliament_constituency_name`.

## Search fields and dependencies

| `field` | Name source | Required extra view |
| --- | --- | --- |
| `parliament_constituency_name` | Supplied `parliament_constituency_name` | None |
| `state_name` | Supplied `state_name` | None |
| `english` | Supplied `parliament_constituency_name` | None |

## Exact filters

| Value type | Filters |
| --- | --- |
| Code | `parliament_constituency_code`, `state_code` |
| Text | `parliament_constituency_name`, `state_name` |

[Value rules and missing-value predicates](../QUERIES.md#identifiers-filters-and-matching).

## CLI

```sh
lgd-query parliament_constituencies code 480
```
