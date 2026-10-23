"""GitHub job orchestration; the scrape CLI remains a local DAG runner.

Run from lgd/: python -m utils.daily_workflow <command>.
Only this module knows about release handoffs, job outputs and workflow retries.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from graphlib import TopologicalSorter
from pathlib import Path

from scrape import get_all_downloaders
from scrape.base import BaseDownloader, Context, Params, get_date_str, setup_logging
from scrape.site_map import get_known_site_map
from .workflow_common import GitHub, digest, output, require_uploaded, verify_download, run_bounded
from . import component_capacity


logger = logging.getLogger(__name__)

DEFAULT_MAX_JOBS = 3
WORKERS_PER_JOB = 10
RELEASE_CAPACITY = 990  # Leave space below GitHub's 1,000-asset limit for indexes.
RELEASE_PATTERN = re.compile(r'lgd-latest(?:-extra([1-9][0-9]*))?')


def downloaders():
    BaseDownloader.clear_cache()
    BaseDownloader.set_known_site_map(get_known_site_map())
    params = Params()
    params.read_timeout = 300
    params.captcha_retries = 10
    params.captcha_model_dir = 'data/captcha/models'
    items = get_all_downloaders(Context(params))
    result = {item.name: item for item in items}
    if len(result) != len(items):
        raise ValueError('Duplicate component names')
    graph = {name: sorted(item.deps) for name, item in result.items()}
    unknown = {dep for deps in graph.values() for dep in deps} - result.keys()
    if unknown:
        raise ValueError(f'Unknown dependencies: {sorted(unknown)}')
    order = tuple(TopologicalSorter(graph).static_order())
    return {name: result[name] for name in order}


def asset_name(downloader, collection_date):
    filename = downloader.csv_filename
    if downloader.name == 'TRANSACTIONS':
        return filename + '.7z'
    return f'{Path(filename).stem}.{collection_date}.csv.7z'


def release_inventory(github):
    releases = []
    for release in github.api('releases?per_page=100', paginate=True):
        match = RELEASE_PATTERN.fullmatch(release['tag_name'])
        if match:
            if release['draft']:
                raise ValueError(f'Unexpected draft release: {release["tag_name"]}')
            releases.append(dict(id=release['id'], tag=release['tag_name'],
                                 number=int(match[1] or 0), assets=github.assets(release['id'])))
    releases.sort(key=lambda release: release['number'])
    if not releases or releases[0]['number'] != 0:
        raise ValueError('The lgd-latest release must already exist')
    return releases


def allocate(items, releases, collection_date):
    """Reserve unique destinations before uploads start; no concurrent placement."""
    counts = {release['tag']: len(release['assets']) for release in releases}
    existing = {}
    requested = {asset_name(item, collection_date) for item in items.values()}
    for release in releases:
        for asset in release['assets']:
            if asset['name'] not in requested:
                continue
            if asset['name'] in existing:
                raise ValueError(f'Duplicate asset across releases: {asset["name"]}')
            existing[asset['name']] = release
    plan = {}
    for name, downloader in items.items():
        filename = asset_name(downloader, collection_date)
        if name == 'TRANSACTIONS':
            release = releases[0]
        elif filename in existing:
            release = existing[filename]
        else:
            release = next((r for r in releases if counts[r['tag']] < RELEASE_CAPACITY), None)
            if release is None:
                number = releases[-1]['number'] + 1
                release = dict(id=None, tag=f'lgd-latest-extra{number}', number=number, assets=[])
                releases.append(release)
                counts[release['tag']] = 0
            counts[release['tag']] += 1
        plan[name] = dict(release_id=release['id'], release_tag=release['tag'],
                          asset_name=filename)
    return plan


def prepare(github):
    # created_at is stable across retries, unlike the runner's wall clock.
    run = github.api(f'actions/runs/{int(os.environ["GITHUB_RUN_ID"])}')
    collection_date = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00')) \
        .astimezone(timezone.utc).strftime('%d%b%Y')
    items = downloaders()
    max_jobs = int(os.environ.get('LGD_MAX_COMPONENT_JOBS') or DEFAULT_MAX_JOBS)
    component_capacity.validate_limit(max_jobs)
    releases = release_inventory(github)
    plan = allocate(items, releases, collection_date)
    for release in releases:
        if release['id'] is None:
            created = github.api('releases', '--method', 'POST', '-f', f'tag_name={release["tag"]}',
                                 '-f', f'target_commitish={os.environ["GITHUB_SHA"]}',
                                 '-f', f'name=Local Government Directory Current Month dumps Supplementary{release["number"]}',
                                 '-f', 'make_latest=false')
            release['id'] = created['id']
            for assignment in plan.values():
                if assignment['release_tag'] == release['tag']:
                    assignment['release_id'] = created['id']
    output('date', collection_date)
    output('plan', plan)
    output('capacity', str(component_capacity.create(github, max_jobs)))


def extract_csv(archive, member, destination):
    """Only expose a CSV after the extractor has successfully finished."""
    listing = subprocess.run(['7z', 'l', '-slt', '-ba', str(archive)],
                             check=True, capture_output=True, text=True)
    names = [line.removeprefix('Path = ') for line in listing.stdout.splitlines()
             if line.startswith('Path = ')]
    if names != [member]:
        raise ValueError(f'Unexpected archive members: {names}; expected {member}')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.tmp')
    try:
        with temporary.open('wb') as target:
            subprocess.run(['7z', 'e', '-so', str(archive), member], stdout=target, check=True)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def restore_dependencies(github, component, items, needs, collection_date):
    for name in items[component].deps:
        job = needs[name]
        if job['result'] != 'success':
            raise ValueError(f'Prerequisite {name} did not succeed')
        receipt = json.loads(job['outputs']['published'])
        if receipt['component'] != name or receipt['date'] != collection_date:
            raise ValueError(f'Wrong prerequisite receipt: {name}')
        expected = asset_name(items[name], collection_date)
        if receipt['asset']['name'] != expected or not receipt['asset'].get('digest'):
            raise ValueError(f'Incomplete prerequisite receipt: {name}')
        with tempfile.TemporaryDirectory(prefix='lgd-dependency-') as folder:
            archive = Path(folder) / expected
            download_prerequisite(github, receipt['asset'], archive)
            extract_csv(archive, expected.removesuffix('.7z'), items[name].get_filename())


def download_prerequisite(github, asset, destination):
    try:
        github.download(asset, destination)
        return
    except subprocess.CalledProcessError as error:
        if b'HTTP 404' not in (error.stderr or b''):
            raise
        # The monthly workflow can redistribute assets between attempts of a
        # failed daily run. Locate the same immutable file under its new ID,
        # but require the original checksum; never substitute a fresh scrape.
        for release in release_inventory(github):
            for candidate in release['assets']:
                if candidate['name'] != asset['name'] or candidate['size'] != asset['size']:
                    continue
                if candidate.get('digest') and candidate['digest'] != asset['digest']:
                    continue
                github.download(dict(candidate, digest=asset['digest']), destination)
                return
        raise


def seed_transactions(github, release_id, downloader):
    """Seed current published history even on retry; keep unfinished range files."""
    history = downloader.history_dir
    history.mkdir(parents=True, exist_ok=True)
    asset = github.find_asset(release_id, 'transactions.csv.7z')
    if asset is None:
        if downloader.previous_file.exists() or downloader.coverage_file.exists():
            raise ValueError('Cached transaction history exists but the published history is missing')
        return
    with tempfile.TemporaryDirectory(prefix='lgd-transactions-') as folder:
        archive = Path(folder) / asset['name']
        github.download(asset, archive)
        # Fetch both before changing either checkpoint. Data is replaced before
        # coverage, so interruption can only cause safe refetching/deduplication.
        coverage = github.find_asset(release_id, 'transactions_dates_covered.txt')
        coverage_path = Path(folder) / 'dates_covered.txt'
        if coverage and coverage.get('size', 0):
            github.download(coverage, coverage_path)
        else:
            coverage_path.write_text('')
        extract_csv(archive, 'transactions.csv', downloader.previous_file)
        temporary = downloader.coverage_file.with_suffix('.tmp')
        temporary.write_bytes(coverage_path.read_bytes())
        temporary.replace(downloader.coverage_file)
    Path(downloader.get_filename()).unlink(missing_ok=True)


def scrape_component(component):
    # This subprocess uses the scraper's scheduler, with only the selected
    # parent in its graph. All its children share the component's worker pool.
    from scrape.__main__ import run_on_threads
    from scrape.captcha_helper import CaptchaHelper

    setup_logging(logging.INFO)
    items = downloaders()
    downloader = items[component]
    missing = [name for name in downloader.deps if not items[name].is_done()]
    if missing:
        raise ValueError(f'Missing released prerequisites: {missing}')
    CaptchaHelper.check_models(downloader.ctx.params.captcha_model_dir)
    workers = WORKERS_PER_JOB
    logger.info('Running %s with up to %s child downloads', component, workers)
    done, errors = run_on_threads({component: []}, items, workers, True,
                                 downloader.ctx.params, status_outfile='status.json')
    return 0 if done == {component} and not errors else 1


def make_archive(downloader, name, directory):
    source = Path(downloader.get_filename()).resolve()
    member = name.removesuffix('.7z')
    linked = directory / member
    os.link(source, linked)  # Same runner filesystem; no second copy of a large CSV.
    destination = directory / name
    temporary = directory / (name + '.tmp')
    subprocess.run(['7z', 'a', '-t7z', str(temporary), member], cwd=directory, check=True)
    temporary.replace(destination)
    return destination


def published_receipt(github, component, collection_date, asset, local_archive=None):
    require_uploaded(asset)
    if local_archive is not None:
        verify_download(local_archive, asset)
    if not asset.get('digest'):
        # Older assets can lack the server checksum. Read the published bytes
        # once, so every dependency handoff still has a pinned hash.
        with tempfile.TemporaryDirectory(prefix='lgd-verify-') as folder:
            path = Path(folder) / asset['name']
            github.download(asset, path)
            checksum = digest(path)
        if local_archive and checksum != digest(local_archive):
            raise ValueError('Published archive differs from the completed upload')
        asset = dict(asset, digest=f'sha256:{checksum}')
    return dict(component=component, date=collection_date,
                asset={key: asset[key] for key in ('id', 'name', 'size', 'state', 'digest')})


def run_component(github, component, assignment, needs):
    items = downloaders()
    downloader = items[component]
    collection_date = get_date_str()
    name = asset_name(downloader, collection_date)
    release_id = assignment['release_id']
    release_tag = assignment['release_tag']
    existing = github.find_asset(release_id, name)
    if existing and existing.get('state') == 'starter' and existing.get('size') == 0:
        # A failed GitHub upload can leave an empty placeholder. Never delete
        # a complete archive when retrying a daily upload.
        github.api(f'releases/assets/{int(existing["id"])}', '--method', 'DELETE')
        existing = None
    if existing and component != 'TRANSACTIONS':
        output('published', published_receipt(github, component, collection_date, existing))
        return 0

    restore_dependencies(github, component, items, needs, collection_date)
    if component == 'TRANSACTIONS':
        seed_transactions(github, release_id, downloader)
    Path('status.json').unlink(missing_ok=True)
    code = run_bounded([sys.executable, '-m', 'utils.daily_workflow', 'scrape', component])
    if code:
        return code
    status = json.loads(Path('status.json').read_text())
    if status != {'done': [component], 'error': [], 'left': []} or not downloader.is_done():
        raise ValueError(f'Component did not produce a complete report: {component}')
    # Keep compression/upload scratch beside the raw data, so hardlinks work.
    with tempfile.TemporaryDirectory(prefix='publish-', dir='data') as folder:
        archive = make_archive(downloader, name, Path(folder).resolve())
        github.upload(release_tag, archive, replace=component == 'TRANSACTIONS')
        asset = github.find_asset(release_id, name)
        receipt = published_receipt(github, component, collection_date, asset, archive)
        if component == 'TRANSACTIONS':
            coverage = Path(folder) / 'transactions_dates_covered.txt'
            coverage.write_bytes(downloader.coverage_file.read_bytes())
            github.upload(release_tag, coverage, replace=True)
        output('published', receipt)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run', 'scrape'])
    parser.add_argument('component', nargs='?')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(GitHub())
        return 0
    if args.component not in downloaders():
        parser.error('An active component is required')
    if args.command == 'scrape':
        return scrape_component(args.component)
    return run_component(GitHub(), args.component, json.loads(os.environ['LGD_ASSIGNMENT']),
                         json.loads(os.environ['LGD_NEEDS']))


if __name__ == '__main__':
    sys.exit(main())
