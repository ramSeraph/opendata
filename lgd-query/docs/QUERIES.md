# Dataset queries

The [dataset index](datasets/README.md) covers all 39 Parquet reports, with one
document per dataset. These APIs are unreleased; PyPI 0.1.0 contains the general
metadata, download and SQL interfaces only.

The [organization data guide](ORGANIZATION_DATA.md) diagrams the reports,
their source fields and the name lookups that cross dataset boundaries.

## Connections and dependencies

Each dataset has a module under `lgd_query.queries`. Helpers return native
DuckDB relations and accept an existing connection. No scraper, converter,
history package, Pandas or Arrow is needed.

```python
from lgd_query import load_release, connect, queries
from lgd_query.queries import villages, constituencies_mapping_urban

release = load_release()
with connect(queries.sources(release, "villages"), cache_dir="./data") as db:
    rows = villages.search(db, "Rampur", state_code="9").fetchall()

# This mapping has state codes but no state names. The dependency helper loads
# states from the same metadata generation, and the query joins by state code.
inputs = queries.sources(release, "constituencies_mapping_urban", field="state_name")
print([(source.name, source.observed_on, source.status) for source in inputs])
with connect(inputs, cache_dir="./data") as db:
    rows = constituencies_mapping_urban.search(
        db, "Kerala", field="state_name", mode="exact"
    ).fetchall()
```

`queries.required_datasets(dataset, field=...)` lists required view names
without reading metadata. `queries.sources(release, dataset, field=...,
observed_on=None)` returns the corresponding `Dataset` objects from a pinned
release. Pass the selected search field, including `english` where applicable.
Listing and code lookups normally need only the queried report. State and central
organization-unit queries can pass `include_entity_name=True` to both the
dependency helper and query method to add location labels from `org_unit_details`.

Python callers open these inputs with `connect`; the CLI does it automatically.
Unavailable dependencies fail explicitly. An `observed_on` guard applies to
every participating report. A single generation can contain different report
dates, so inspect each input when that matters. Loading a name reference does
not establish a historical relationship at the primary report's date.

Names already supplied in a report remain as reported. Missing name fields
with a documented code relationship use the reference sources listed in that
dataset's document. Lookup searches add `lookup_names`, an array of all distinct
resolved labels. Several labels do not multiply the primary source rows; an
unresolved reference does not match a name search. Exact duplicate source rows
remain duplicates. Fuzzy lookup results use the smallest distance among the
resolved names. Names never serve as join keys.

Some fields resolve against more than one report. For example, both traditional
local-body parent fields search the traditional and PRI body registers by code
and state. Their `lookup_names` contains distinct labels from both sources;
neither register overrides the other. Resolving a label does not establish that
the source's parent assertion is correct.

Organization-unit `list`, `by_code` and `search` support optional location-name
output, independently of which field is searched. With `include_entity_name=True`,
`entity_names` contains all distinct matching details labels; `entity_name` is
the sole label if unambiguous, otherwise NULL. Missing references have an empty
array and NULL. Units and their source columns remain intact. The CLI's
`--include-entity-name` flag loads the dependency automatically; explicit date
guards apply to every input. See the [state](datasets/state_org_units.md#include-the-location-name)
and [central](datasets/central_org_units.md#include-the-location-name) examples.

## Typed entity references

[`constituency_coverage.entities`](datasets/constituency_coverage.md#follow-entity-codes-to-their-registers)
follows typed entity codes to full district, subdistrict, village, local-body
or ward records. Use its `entity_sources` helper to load the corresponding
registers from one release. The CLI exposes the same lookup through
`lgd-query constituency_coverage entities --entity-type SubDistrict --entity-code 1013`.

Organization directories and details also expose `entities(db, entity_type=...,
**filters)` for their numeric location types. `org_unit_coverage.entities` uses
`covered_entity_type` and follows coverage targets instead. Their
`entity_sources` and `required_entity_datasets` helpers load the selected
registers. Geographic, local-body and custom administrative-unit namespaces
are described in the [organization lookup guide](ORGANIZATION_DATA.md#follow-entity-references-to-registers).
These methods return full entity records, retain reference variants and expose
local-body type disagreements; they do not replace the source office/claim rows.

```sh
lgd-query state_org_units entities --entity-type 2 --organization-unit-code 1237173
lgd-query org_unit_coverage entities --covered-entity-type Village --coverage-type F
```

## Reported LGD-to-ECI constituency codes

Both [`constituencies_mapping_pri`](datasets/constituencies_mapping_pri.md#eci-code-lookup)
and [`constituencies_mapping_urban`](datasets/constituencies_mapping_urban.md#eci-code-lookup)
provide `eci_codes(db, level="assembly"|"parliament", constituency_code=None,
state_code=None, eci_code=None)`. The main constituency registers supply LGD
codes only. The mapping helpers return distinct reported LGD/ECI pairs with
all supplied names and forward/reverse ambiguity flags. They do not certify
or correct electoral identifiers. ECI numbers require constituency level,
state and the relevant electoral period; they are not national identifiers.

Use one dated report view and inspect its source date. The PRI report stops
in October 2022; it is not substituted with urban data when unavailable.

## Identifiers, filters and matching

`list` returns all source rows unless filtered. `by_code` returns every matching
row in the documented primary code namespace; it is not a uniqueness assertion.
Transactions use `by_id`. Census lookup is offered only for a documented census
year of the primary entity. Other identifiers, such as ECI codes, have their own
named filters and are never interpreted as LGD codes.

States, districts and subdistricts have explicit function signatures. The other
modules accept validated `**filters` named after their report columns. Their
documents enumerate accepted filters and types. Supplied filters combine with
AND; `None` leaves one unused. Exact text filters preserve source spelling and
case. Use `search(field=...)` for normalized name matching. String identifiers
retain leading zeros; numeric input does not infer padding. Organization-specific
codes, transaction IDs, ward numbers and pincodes remain text. Signed source
sentinels are accepted only for documented signed fields.

Search modes are `exact`, `prefix`, `contains` (default), and `fuzzy`. Comparison
trims outer whitespace, normalizes Unicode to NFC and lowercases. It does not
transliterate or remove accents. `%`, `_` and quotes are literal. Missing/blank
names do not match; local-name searches do not fall back to English.

Fuzzy mode adds `distance` and accepts `max_distance=2` and
`metric="levenshtein"|"damerau_levenshtein"`. DuckDB's distances count UTF-8 bytes
for non-ASCII text, not Unicode characters or graphemes. All filters and the
distance threshold apply before `limit` (default 20; Python `None` means all).
Results sort by name and report code/scope, with distance first for fuzzy search.
Ties between identical keys/labels do not imply an authoritative variant.

Events support inclusive `since`/`until` dates. Their row dates describe reported
events, not complete collection coverage or a reconstructed snapshot. Changes
and constituency coverage require `entity_type` when filtering `entity_code`.
Other polymorphic code filters return all supplied namespaces unless additionally
scoped by type; no target type is guessed from a bare number.

## CLI

```sh
lgd-query subdistricts list --state-code 32 --district-code 559
lgd-query villages search Rampur --state-code 9 --format json
lgd-query pri_local_bodies search NAME --field parent_local_body_name
lgd-query constituencies_mapping_urban search Kerala --field state_name --mode exact
lgd-query pincode_villages list --pincode 691001
lgd-query changes code 123 --entity-type Village --since 2024-01-01
lgd-query transactions search renamed --since 2024-01-01 --until 2024-12-31
```

Each dataset has `list`, `code` (transactions: `id`), `search`, and census commands
where applicable. Column filters become flags with hyphens. Search supports the
same fields/modes as Python. Every command accepts `--cache-dir`, `--observed-on`,
and `--format json|table`. Use command-specific `--help` for supported filters.
JSON contains `columns` and `rows`. Wide reports use field/value tables so names
remain visible at ordinary terminal widths.

Use `queries.DATASETS` to enumerate modules, or `queries.get(name)` to select one
programmatically. New dataset definitions do not claim that a retired or
currently unavailable report has a downloadable latest release.
