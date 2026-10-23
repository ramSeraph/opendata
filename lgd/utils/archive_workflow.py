"""Workflow adapters: parallel archive builds, serialized safe finalization."""

import argparse
import json
import os
import re
import shlex
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import archive_prev_month as archive
from .workflow_common import GitHub, output, run_bounded


def month_for_run(created_at, months_back):
    if months_back < 1:
        raise ValueError('Only completed months can be archived')
    day = datetime.fromisoformat(created_at.replace('Z', '+00:00')).astimezone(timezone.utc)
    for _ in range(months_back):
        day = day.replace(day=1) - timedelta(days=1)
    return day.strftime('%b%Y')


def plan_archives(month):
    releases = archive.get_all_releases()
    latest = archive.filter_releases(releases, 'lgd-latest')
    archived = archive.filter_releases(releases, 'lgd-archive')
    archived.sort(key=lambda tag: 0 if tag == 'lgd-archive' else int(tag.rsplit('extra', 1)[1]))
    if not archived or archived[0] != 'lgd-archive':
        raise ValueError('The lgd-archive release must already exist')
    sources = archive.get_all_archive_names(latest)
    published = archive.get_all_archive_names(archived)
    counts = {tag: sum(value == tag for value in published.values()) for tag in archived}
    by_file = archive.get_mapping(name for name in sources if name.endswith(f'{month}.csv.7z'))
    result = []
    for prefix, dates in sorted(by_file.items()):
        if not re.fullmatch(r'[a-z][a-z0-9_]*', prefix):
            raise ValueError(f'Invalid dataset filename: {prefix}')
        filename = f'{prefix}.{month}.7z'
        existing = published.get(filename)
        target = existing or next((tag for tag in archived if counts[tag] < 990), None)
        if target is None:
            number = 1 if archived[-1] == 'lgd-archive' else int(archived[-1].rsplit('extra', 1)[1]) + 1
            target = f'lgd-archive-extra{number}'
            archive.run_external(shlex.join([
                'gh', 'release', 'create', target, '--latest=false', '--target', os.environ['GITHUB_SHA'],
                '--title', f'Local Government Directory monthly archives Supplementary{number}',
                '--notes', 'Supplementary storage for the LGD monthly archives.']))
            archived.append(target)
            counts[target] = 0
        if not existing:
            counts[target] += 1
        dates = sorted(set(dates))
        names = [f'{prefix}.{day}.csv.7z' for day in dates]
        result.append(dict(prefix=prefix, month=month, dates=dates, target=target,
                           published=existing, sources={name: sources[name] for name in names}))
    return result


def build(item):
    staging = Path('data/zipping_area')
    staging.mkdir(parents=True, exist_ok=True)
    name = f'{item["prefix"]}.{item["month"]}.7z'
    # A failed-job retry can reuse a plan made before this asset was uploaded.
    current = archive.get_release_asset(item['target'], name)
    monthly = {name: item['target']} if current is not None else {}
    path, tag, _ = archive.prepare_monthly_archive(
        item['prefix'], item['dates'], item['month'], item['sources'], monthly,
        {item['target']: 0}, [item['target']], staging, target_release=item['target'])
    # The shared helper checked both the members and the actual published bytes.
    # Pass their identity to the coordinator instead of downloading them again.
    remote = archive.get_release_asset(tag, path.name)
    archive.require_uploaded(remote, path.name)
    receipt = dict(run_id=os.environ['GITHUB_RUN_ID'], item=item, release=tag,
                   name=path.name, api_url=remote['apiUrl'], size=path.stat().st_size,
                   sha256=archive.file_digest(path))
    temporary = Path('archive-receipt.json.tmp')
    temporary.write_text(json.dumps(receipt))
    temporary.replace('archive-receipt.json')


def finalize(item, receipt):
    if receipt['run_id'] != os.environ['GITHUB_RUN_ID'] or receipt['item'] != item:
        raise ValueError('Archive receipt does not match this run and dataset')
    name = f'{item["prefix"]}.{item["month"]}.7z'
    if receipt['name'] != name or receipt['release'] != item['target']:
        raise ValueError('Unexpected published archive identity')
    asset = archive.get_release_asset(receipt['release'], name)
    archive.require_uploaded(asset, name)
    if asset['apiUrl'] != receipt['api_url'] or asset['size'] != receipt['size']:
        raise ValueError('Published archive changed after verification')
    if asset.get('digest'):
        if asset['digest'] != 'sha256:' + receipt['sha256']:
            raise ValueError('Published archive checksum changed after verification')
    else:
        # Retain full verification for older uploads lacking a server checksum.
        path = Path('data/combined') / name
        archive.download_published_archive(path, receipt['release'],
                                           [key.removesuffix('.7z') for key in item['sources']])
        if archive.file_digest(path) != receipt['sha256']:
            raise ValueError('Published archive bytes changed after verification')
        path.unlink()

    # Only this serialized job may update mapping or remove original daily data.
    archive.update_mapping(item['prefix'], item['dates'])
    current = archive.get_all_archive_names(sorted(set(item['sources'].values())))
    for name, tag in item['sources'].items():
        # A retried finalizer can encounter files it already deleted.
        if name in current:
            if current[name] != tag:
                raise ValueError(f'Daily asset moved unexpectedly: {name}')
            archive.run_external(shlex.join(['gh', 'release', 'delete-asset', tag, name, '-y']))
    archive.refresh_indexes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'compress', 'build', 'finalize', 'settle'])
    args = parser.parse_args()
    if args.command == 'prepare':
        github = GitHub()
        run = github.api(f'actions/runs/{int(os.environ["GITHUB_RUN_ID"])}')
        month = month_for_run(run['created_at'], int(os.environ.get('LGD_ARCHIVE_NUM_MONTHS_BACK') or 1))
        items = plan_archives(month)
        output('month', month)
        output('has-work', 'true' if items else 'false')
        output('matrix', {'include': items})
        return 0
    if args.command == 'settle':
        releases = archive.filter_releases(archive.get_all_releases(), 'lgd-latest')
        archive.redistribute_latest(releases)
        archive.refresh_indexes()
        return 0
    item = json.loads(os.environ['LGD_ARCHIVE_ITEM'])
    if args.command == 'build':
        build(item)
    elif args.command == 'compress':
        Path('archive-receipt.json').unlink(missing_ok=True)
        code = run_bounded([sys.executable, '-m', 'utils.archive_workflow', 'build'])
        if code:
            return code
        output('receipt', json.loads(Path('archive-receipt.json').read_text()))
    else:
        finalize(item, json.loads(os.environ['LGD_ARCHIVE_RECEIPT']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
