"""Find remaining daily release assets and plan one job per closed-month dataset."""

import argparse
from collections import defaultdict
from datetime import UTC, date, datetime
import json
import os
from pathlib import Path
import re

from .archive_prev_month import filter_releases, get_all_archive_names, get_all_releases


DAILY_ARCHIVE = re.compile(r'([a-z][a-z0-9_]*)\.(\d{2}[A-Z][a-z]{2}\d{4})\.csv\.7z')


def build_plan(names, *, today=None, month='', component=''):
    today = today or datetime.now(UTC).date()
    cutoff = today.replace(day=1)
    selected_month = None
    if month:
        if not re.fullmatch(r'\d{4}-\d{2}', month):
            raise ValueError('Month must use YYYY-MM format')
        selected_month = date.fromisoformat(month + '-01')
        if selected_month >= cutoff:
            raise ValueError('Catch-up can only process completed months')
    if component and not re.fullmatch(r'[a-z][a-z0-9_]*', component):
        raise ValueError('Component must be a dataset filename prefix, e.g. villages')

    grouped = defaultdict(set)
    for name in names:
        match = DAILY_ARCHIVE.fullmatch(name)
        if not match:
            continue
        prefix, date_text = match.groups()
        snapshot = datetime.strptime(date_text, '%d%b%Y').date()
        snapshot_month = snapshot.replace(day=1)
        if snapshot_month >= cutoff:
            continue
        if selected_month and snapshot_month != selected_month:
            continue
        if component and prefix != component:
            continue
        grouped[snapshot_month, prefix].add(snapshot)

    jobs = [{'month': month_start.strftime('%b%Y'), 'component': prefix, 'snapshots': len(days)}
            for (month_start, prefix), days in sorted(grouped.items())]
    if len(jobs) > 256:
        raise ValueError('Backlog exceeds 256 jobs; select a month or component to narrow this run')
    return jobs


def publish_plan(jobs, output):
    matrix = {'include': jobs}
    Path(output).write_text(json.dumps(matrix, indent=2) + '\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with Path(os.environ['GITHUB_OUTPUT']).open('a') as destination:
            destination.write(f'matrix={json.dumps(matrix, separators=(",", ":"))}\n')
            destination.write(f'has_work={str(bool(jobs)).lower()}\n')

    summary = f'Found {len(jobs)} pending monthly archives containing {sum(j["snapshots"] for j in jobs)} daily files.\n'
    if jobs:
        summary += '\nEach archive gets its own four-hour compression window. Jobs run one at a time.\n'
        summary += '\n| Month | Dataset | Daily files |\n|---|---|---:|\n'
        summary += ''.join(f'| {j["month"]} | {j["component"]} | {j["snapshots"]} |\n' for j in jobs)
    else:
        summary += '\nNo unfinished archives match this selection.\n'
    print(summary, end='')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as destination:
            destination.write(summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', default='', help='Optional completed month in YYYY-MM format')
    parser.add_argument('--component', default='', help='Optional dataset filename prefix')
    parser.add_argument('--output', default='archive_catchup_plan.json')
    args = parser.parse_args()
    # Validate user selection before requesting release metadata.
    build_plan([], month=args.month, component=args.component)
    releases = filter_releases(get_all_releases(), 'lgd-latest')
    remaining = get_all_archive_names(releases)
    publish_plan(build_plan(remaining, month=args.month, component=args.component), args.output)


if __name__ == '__main__':
    main()
