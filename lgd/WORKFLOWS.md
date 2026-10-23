# LGD daily and monthly workflows

## Daily component DAG

The daily run is scheduled for 07:25 UTC (12:55 PM IST).

The dependency declarations on the scraper's downloader objects are the source
of truth. Generate the checked-in workflow after changing those declarations:

```sh
cd lgd
uv run python -m utils.generate_daily_workflow
uv run python -m utils.generate_daily_workflow --check
```

The preparation job checks this generated file before doing any work. Workflows
never commit changes. There is one GitHub job per active component, with `needs`
matching its direct prerequisites. State, organization and department children
stay inside their component and share ten download workers. A failed component
blocks its dependents; independent branches continue.

`LGD_MAX_COMPONENT_JOBS`, a repository variable, defaults to **3**. Preparation
assigns components to that many queued concurrency slots. Each slot runs one
component at a time, giving at most three component jobs and thirty concurrent
downloads by default. Slot assignment is fixed for a run; an idle slot cannot
take work assigned to a busy slot. GitHub's `queue: max` preserves pending jobs
instead of cancelling them as the default concurrency behavior would.

Preparation also reserves destinations in `lgd-latest` and its existing
`-extraN` namespace. A component uploads its completed archive directly to its
assigned release. Its dependents receive the exact asset ID, date and SHA-256,
download the archive, verify it and extract the prerequisite CSV atomically.
If monthly redistribution moved that asset between retry attempts, its new ID
is accepted only when the downloaded bytes match the original checksum.
Successful dated uploads are reused on retry. Only the cumulative transactions
report and its coverage file retain their existing replacement behavior: data
is published before coverage, and retries seed from the currently published
history before merging additional reports.

One final job refreshes the shared release listing, including after partial
failure. The daily retry trigger reruns failed jobs and their dependents, up to
three attempts. Unfinished children are cached separately for each component
and workflow run; a new day's scrape does not reuse an old day's reports.

The UTC date of the original run is fixed across jobs, retries and midnight.
`LGD_COLLECTION_DATE` supplies that date to the shared filename/date helper.
The scraper CLI is unchanged: `python -m scrape` continues to run its local DAG.
GitHub-specific behavior lives in `utils/daily_workflow.py` and
`utils/workflow_common.py`.

## Monthly archive matrix

Preparation selects the completed month using the original run timestamp and
`LGD_ARCHIVE_NUM_MONTHS_BACK` (default **1**). It discovers the remaining daily
files and reserves archive release destinations before workers begin.

Each dataset gets a compression job and a dependent finalization job. The
compression matrix has **no `max-parallel` cap**, and `fail-fast: false` lets
other datasets finish after a failure. GitHub's available runners govern
compression concurrency. Workers use the same archive checks and atomic
temporary-file handling as the sequential archive script, then verify their
published archive. They never delete daily assets or change the shared mapping.

Finalizers share a single queued concurrency group. Each checks its worker's
verified archive identity, updates and verifies the backed-up archive mapping,
then removes the covered daily files and refreshes the indexes. A changed or
incomplete archive cannot authorize deletion. A retry can safely finish after
some daily files were already deleted. Old assets without a server checksum
retain the full download/integrity verification path.

Redistribution and a final index refresh run after all matrix jobs finish. The
monthly retry trigger retains full-run retries so preparation discovers current
asset locations after redistribution. The standalone archive CLI retains its
sequential behavior.

## Time budgets and coordination

Daily component jobs and archive compression jobs have a **four-hour** job
limit. Their heavy subprocess work stops after **3½ hours**, leaving time for
publication and checkpoint saving. The helper terminates the whole worker
process group before saving caches. A job that repeatedly cannot finish one
component within this budget still needs that component split further; a matrix
does not remove the per-job time limit.

The daily and monthly workflows share the `lgd-raw-releases` concurrency group.
They queue behind one another so archiving/redistribution cannot remove a
prerequisite asset while a daily DAG is using it. Component upload jobs do not
update shared metadata concurrently. No workflow performs Git commits.

GitHub references: [job dependencies](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-jobs),
[queued concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
and [job limits](https://docs.github.com/en/actions/reference/limits).
