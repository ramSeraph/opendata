# Organization and unit explorer

An offline, interactive graph for understanding the latest LGD central and state
organization records. The explicit government selector offers **Centre** and each
state/UT from the current state register. It includes no historical versions or
date selector. Centre is the default selection.

From the repository root, with DuckDB available in the LGD environment:

```sh
lgd/.venv/bin/python lgd/visualizations/central_orgs/build.py
```

Open `lgd/data/central-org-graph/index.html` in a current browser. **Keep the
`scopes/` folder beside it.** It needs no server or internet access. Centre is
embedded in the HTML; a state's compressed data is loaded from a relative local
script only when selected. Only one scope is decompressed into a graph at a time,
so the browser does not need to load every state's units together. The browser
must support `DecompressionStream('gzip')`.

`scopes.json` lists the available governments and bundle sizes. The output also
contains Centre's data as `data.json.gz`, each selection as
`scopes/scope-<state_code>.json.gz`, and source hashes/checks in `validation.json`.
The existing directory name is retained for compatibility. This standalone
build does not publish a website. The GitHub Pages integration is described in
[the website guide](../../../docs/README.md); it uses the same explorer with
verified published Parquets and lazily loads Centre as well as state bundles.
Override the input/output locations with `--data-dir` and `--output`.

The builder pins each dataset's `iceberg.json`, follows its exact current
Parquet reference and records hashes. It does not infer the newest generation
from filenames. It strips history-interval metadata. Only the last observation
ledger entry is read to describe source provenance and the freshness of carried
current records; no observation series is included.

## Reading the graph

- Organization-to-organization edges come from `parent_organization_code`.
- Office-to-office edges come from `parent_organization_unit_code`.
- Organization membership comes from each unit's `organization_code`. A root
  unit without a parent office stays an organization member; it is not attached
  to a guessed head office.
- Large sets of units without parent offices are grey display groups, grouped
  by their own `organization_level_code`. These are not LGD entities or new
  source edges. Expanding a group shows all its members.
- Dashed reference cards preserve parents or organizations absent from their
  independent registers. They are not presented as supplied directory rows.
- Each unit's **Location** control toggles a single box beside its card, showing
  the location name, type and entity code. **Coverage** toggles a separate,
  searchable list of supplied coverage records, with full/partial flags. Empty
  `coverage_details_reported=false` placeholders are omitted from both the toggle
  count and the list. A unit with only such a placeholder shows a disabled
  **Coverage 0** control. Genuine coded records stay
  included even if the source leaves their name or type label blank. The list
  scrolls through all supplied records without child paging. The inspector's
  **Coverage** tab retains the original placeholder rows for inspection;
  zero supplied records does not establish that a unit has no coverage.
  One reference box is open at a time; choosing the other control switches it.
  Neither box adds hierarchy nodes, changes child/title expansions, nor moves
  or zooms the graph. Boxes follow the unit when panning and remain within the
  graph viewport. Close with the same control, the × button, or Escape.
  **View source details** opens the existing inspector tab for that unit.
- Empty **Coverage**, **Titles** and **Location** controls are disabled on both
  cards and the inspector. **Location 0** means the unit's entity type or code
  is blank or zero. A nonzero reference with a missing name remains expandable.
- Each unit's **Titles** control independently opens all matching designations.
  The ordinary child control counts and opens child units only. Opening or
  collapsing children leaves the title expansion unchanged, and vice versa.
  Purple designations are matched on organization and
  the unit's own nonblank level code. Edges say “designation for this unit’s
  level”; they are derived joins, not reported parent edges or staff assignments.
  Select a title to inspect both matching source rows while keeping its unit
  in view. A shared title can appear under several matching units; each display
  occurrence retains the same source association ID.
- Organizations link to a separate designation **source catalogue** from their
  inspector. This preserves every title–organization–level association, including
  blank level codes that cannot be matched to units. Catalogue folders are not
  shown as organization children in the main hierarchy.

Search names or codes, click a card to inspect the source fields, click its
plus/minus control to expand/collapse children, or double-click to focus on its
branch. Breadcrumbs and the Parent button move upward. The inspector also has
keyboard-accessible child links. `↑ Parent` is a button, `/` focuses search,
and the left/right arrow keys collapse/expand the selected record.
Expanding and collapsing either children or titles preserve the current zoom and the screen
position of the node being expanded. **Fit** deliberately reframes the graph;
focusing a different branch also sets a fresh view.
The **Title branches** checkbox controls the visibility of open title branches, and the **Titles** search
filter searches designation names, codes, organizations and reported levels.
Search, examples, organization listings, source inspection and downloads follow
the selected government. Switching back restores that government's focus,
selection, independently expanded child/title branches, the open reference box
and its coverage search/scroll position, search, filters, zoom and pan for the
current browser session. The URL records the government, focused branch and
selected record, so reloading preserves that context. Older URLs without a
government selection continue to open Centre.

Name searches tolerate small spelling errors, adjacent transpositions and
partial words, in any order. `dept`, `deptt` and `govt` expand to their usual
full words. Exact codes and exact names rank first, followed by literal matches
and then fuzzy matches; ties retain organization depth ordering. Numeric terms
are never typo-corrected. Short terms stay literal to avoid unrelated matches.
Coverage searches use the same matching rules. Search remains scoped to the
selected government and record kind.
The Telecommunication example opens the department and its CENTRE unit. Choose
**Titles 2** on that unit to see the two matching designations. Vijayawada postal
division has a separate **Titles 1** control. Titles remain closed until explicitly
expanded or revealed by selecting a title association from search or a saved URL.

Expanding a node shows **every immediate child**, without “Next 8” pages, a node
limit, or a depth cutoff. Deeper branches retain their own controls. The toolbar's
**Expand a level** opens ordinary children of all expanded cards; it does not open
unit title associations. The layout retains all expanded records, while drawing
only cards in the viewport and connections whose curves cross it. A connection
remains visible even when its child card is off-screen; strokes are batched to
keep large expanded branches responsive. At overview scales, cards become
compact marks. **Fit** can fit the entire expanded branch.

The inspector's child and designation lists scroll continuously through all
records, with only visible rows rendered. Use the scrollbar to reach a distant
child, then select it to bring it into view. Search works across the entire
selected government, regardless of which branches are open.

The organization list is sorted by ascending parent-chain depth, then
alphabetically within each depth. Depth 0 has no reported parent in the available
graph; missing parent records terminate the chain, so depth describes the
available data rather than a claimed complete governmental hierarchy. Reference
parents count toward their descendants' depth. Organization-filtered search
results use depth as a tie-breaker after match quality.

The initial postal example separates Department of Posts (`1149`), its office
(`1991823`), the location type Postal Circle (`1150`), and the referenced
Andhra Pradesh postal circle (`51466`). The graph starts with this circle's
children. **Location** identifies the Postal Circle separately. Its parent chain is available in the breadcrumbs;
the organization list opens organization-level branches. Automatic layout keeps
cards readable; pan or use **Fit** to see a large branch's full extent.

## Included sources and interpretation

All current central and state organizations, offices, designation associations,
administrative levels and administrative entities are included across the
bundles. The builder pins 14 inputs: five `central_*` tables, their five `state_*`
counterparts, the combined details and coverage tables, and states/districts.
Each selection includes nine tables: its five organization tables plus the four
shared sources. State records and the combined details/coverage reports are
restricted to the selected `state_code`; Centre uses `0`.

**This is the organization's government/report scope, not a location filter.**
A central office in Andhra Pradesh stays under Centre. Selecting Andhra Pradesh
shows the state organizations and their units. Coverage claims remain with their
owning units even when the covered place is elsewhere. Current state/district
registers stay complete in every bundle to provide geographic name lookups.
Dates and CSV downloads for every source are in **Data sources**; state source
rows keep their `state_*` dataset names.

The current exports checked on 25 October 2026 contain 68,728 central and
1,030,225 state unit rows, each unique within its government scope and carrying
one scalar `(entity_type, entity_code)` pair. None has multiple directory location
references. The 592,639 unit-details rows are also unique per scoped unit, with
no type/code disagreements against the directory. A pair may be blank or use
zero (799 central directory rows), so this means **at most one usable reference**,
not a verified location for every unit. Coverage is plural: the current data has
46,004 units with more than one coverage row. These observations describe the
current exports, not a guarantee about future reports.

Details are retained as their own source rows. Location enrichment requires the
same unit, organization, entity type and entity code; a different claim does not
overwrite the directory. Administrative entity names are looked up with both
level code and entity code. Unlabelled entity types remain unlabelled, including
the problematic international references with type `-100`.

Coverage retains every claim, including multiplicity, partial/full flags,
missing type/name labels and explicit no-details records. It is distinct from
an office's location. The coverage report's selection level is never substituted
for the office's own level. Designations are titles associated with organizations
and levels; they do not establish personnel or staffing. Unit-level title views
require an exact, nonblank organization-level code.

Source dates differ. Retained unit records are marked with their actual last
supplied date from the latest ledger. A latest export is not a claim of fresh
reporting for every record. The graph does not infer legal status or deletion.

## Checks

```sh
node --test lgd/visualizations/central_orgs/model.test.cjs
```

The model tests cover distinct identity namespaces, source parent edges versus
membership/grouping, typed location lookups, coverage multiplicity, designation
association identity, exact unit-level joins, repeated display occurrences without
duplicating source rows, depth ordering and cycle handling.
They also test Centre/state isolation with overlapping codes, scoped location
and designation joins, coverage ownership, and empty state datasets.
The build checks unique organization/unit/level IDs within each selection and
audits details and coverage references against its unit register.

`browser-check.mjs` uses a Chrome debugging endpoint (port 9231 by default,
override `LGD_GRAPH_CDP_PORT`) to verify interactive navigation, scoped data
loading, large states, switching and view restoration, state links/reload,
load-failure recovery, and desktop/mobile layouts against the generated output.
