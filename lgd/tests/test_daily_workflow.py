import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scrape.base import get_date_str
from utils import daily_workflow as daily
from utils import workflow_common as common
from utils import generate_daily_workflow as generator


class Dataset:
    def __init__(self, name, deps=()):
        self.name = name
        self.deps = deps
        self.csv_filename = name.lower() + '.csv'

    def get_filename(self):
        return f'data/raw/{get_date_str()}/{self.csv_filename}'

    def is_done(self):
        return Path(self.get_filename()).exists()


class FakeGitHub:
    def __init__(self):
        self.files = {}
        self.metadata = {}
        self.events = []
        self.fail_upload = False

    def add(self, name, contents):
        ident = len(self.metadata) + 1
        asset = dict(id=ident, name=name, state='uploaded', size=len(contents),
                     digest='sha256:' + hashlib.sha256(contents).hexdigest())
        self.metadata[name] = asset
        self.files[ident] = contents
        return asset

    def find_asset(self, release_id, name):
        return self.metadata.get(name)

    def upload(self, tag, path, replace=False):
        self.events.append(('upload', path.name))
        if self.fail_upload:
            raise RuntimeError('upload failed')
        self.add(path.name, path.read_bytes())

    def download(self, asset, path):
        self.events.append(('download', asset['name']))
        path.write_bytes(self.files[asset['id']])
        daily.verify_download(path, asset)


class DailyPlanTests(unittest.TestCase):
    def test_generated_jobs_have_exact_scraper_dependencies_and_no_runtime_commits(self):
        items = daily.downloaders()
        generated = generator.generate(items)
        self.assertEqual(generated, generator.WORKFLOW.read_text())
        for name, downloader in items.items():
            expected = ', '.join(['Prepare', *sorted(downloader.deps)])
            self.assertIn(f'  {name}:\n    needs: [{expected}]\n', generated)
        self.assertNotIn('git commit', generated)
        self.assertNotIn('git push', generated)
        component = generator.WORKFLOW.with_name('lgd_component.yml').read_text()
        self.assertIn('group: lgd-component-slot-${{ needs.Admit.outputs.slot }}\n      queue: max', component)
        self.assertIn('group: lgd-component-admission\n      queue: max', component)
        self.assertIn('    needs: Admit\n', component)
        self.assertIn('ADMISSION_ATTEMPT', component)
        self.assertNotIn('      slot:', generated)
        self.assertIn('capacity-check: ${{ needs.Prepare.outputs.capacity }}', generated)
        self.assertIn('      actions: read\n      checks: write', generated)
        retry = generator.WORKFLOW.with_name('lgd_rerun_trigger.yml').read_text()
        self.assertIn('failed-jobs-only: false', retry)
        self.assertIn('timeout-minutes: 240', component)
        self.assertEqual(daily.WORKERS_PER_JOB, 10)
        self.assertEqual(daily.DEFAULT_MAX_JOBS, 3)

    def test_release_reservations_do_not_preassign_capacity(self):
        items = {f'DATA{i}': Dataset(f'DATA{i}') for i in range(8)}
        old = dict(id=7, tag='lgd-latest', number=0,
                   assets=[{'name': f'older-{i}'} for i in range(daily.RELEASE_CAPACITY - 2)])
        releases = [old]
        plan = daily.allocate(items, releases, '23Oct2026')
        self.assertTrue(all('slot' not in assignment for assignment in plan.values()))
        self.assertEqual(sum(v['release_tag'] == 'lgd-latest' for v in plan.values()), 2)
        self.assertEqual(sum(v['release_tag'] == 'lgd-latest-extra1' for v in plan.values()), 6)
        self.assertEqual(len(releases), 2)

    def test_existing_asset_keeps_destination_even_when_release_is_full(self):
        item = Dataset('STATES')
        names = [{'name': f'older-{i}'} for i in range(daily.RELEASE_CAPACITY)]
        names.append({'name': 'states.23Oct2026.csv.7z'})
        releases = [dict(id=7, tag='lgd-latest', number=0, assets=names)]
        plan = daily.allocate({'STATES': item}, releases, '23Oct2026')
        self.assertEqual(plan['STATES']['release_id'], 7)
        self.assertEqual(plan['STATES']['asset_name'], 'states.23Oct2026.csv.7z')
        self.assertEqual(len(releases), 1)

    def test_date_is_stable_across_jobs_and_explicit_dates_still_work(self):
        with patch.dict(os.environ, LGD_COLLECTION_DATE='23Oct2026'):
            self.assertEqual(get_date_str(), '23Oct2026')
            self.assertEqual(get_date_str(datetime(2024, 1, 1)), '01Jan2024')
        with patch.dict(os.environ, LGD_COLLECTION_DATE='not-a-date'):
            with self.assertRaises(ValueError):
                get_date_str()

    def test_one_component_uses_existing_scheduler_without_running_prerequisites(self):
        child = Mock(name='component')
        child.deps = ['STATES']
        parent = Mock()
        parent.is_done.return_value = True
        with patch.object(daily, 'downloaders', return_value={'VILLAGES': child, 'STATES': parent}), \
                patch('scrape.__main__.run_on_threads', return_value=({'VILLAGES'}, set())) as scheduler, \
                patch('scrape.captcha_helper.CaptchaHelper.check_models'), patch.object(daily, 'setup_logging'):
            self.assertEqual(daily.scrape_component('VILLAGES'), 0)
            self.assertEqual(scheduler.call_args.args[0], {'VILLAGES': []})
            self.assertEqual(scheduler.call_args.args[2:4], (10, True))
            parent.is_done.return_value = False
            scheduler.reset_mock()
            with self.assertRaisesRegex(ValueError, 'Missing released'):
                daily.scrape_component('VILLAGES')
            scheduler.assert_not_called()

    def test_all_components_including_organizations_use_ten_workers(self):
        items = daily.downloaders()
        self.assertTrue({'ORG_UNIT_COVERAGE', 'ORG_UNIT_DETAILS', 'STATE_ORG_UNITS',
                         'STATE_ADMIN_DEPT_UNITS', 'CENTRAL_ADMIN_DEPTS'} <= items.keys())
        for name in items:
            with self.subTest(component=name):
                downloader = Mock()
                downloader.deps = []
                with patch.object(daily, 'downloaders', return_value={name: downloader}), \
                        patch('scrape.__main__.run_on_threads', return_value=({name}, set())) as scheduler, \
                        patch('scrape.captcha_helper.CaptchaHelper.check_models'), \
                        patch.object(daily, 'setup_logging'):
                    self.assertEqual(daily.scrape_component(name), 0)
                self.assertEqual(scheduler.call_args.args[2:4], (10, True))

    def test_deadline_kills_process_group_before_returning_to_cache_step(self):
        process = Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired('scrape', 1), 0]
        with patch.object(daily.subprocess, 'Popen', return_value=process), \
                patch.object(daily.os, 'killpg') as kill, patch.object(common.time, 'sleep'):
            self.assertEqual(daily.run_bounded(['scrape'], 1), 124)
        self.assertEqual([call.args for call in kill.call_args_list],
                         [(12345, signal.SIGTERM), (12345, signal.SIGKILL)])

    def test_failed_or_corrupt_download_preserves_existing_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, GITHUB_REPOSITORY='owner/repo'):
            target = Path(folder) / 'asset.7z'
            target.write_bytes(b'previous complete download')
            asset = dict(id=1, name=target.name, size=10, state='uploaded', digest='sha256:' + '0' * 64)

            def interrupted(command, **kwargs):
                kwargs['stdout'].write(b'partial')
                raise subprocess.CalledProcessError(1, command)

            for behavior, error in ((interrupted, subprocess.CalledProcessError),
                                    (lambda command, **kwargs: kwargs['stdout'].write(b'wrong data'), ValueError)):
                with patch.object(common.subprocess, 'run', side_effect=behavior):
                    with self.assertRaises(error):
                        common.GitHub().download(asset, target)
                self.assertEqual(target.read_bytes(), b'previous complete download')
                self.assertFalse(target.with_name(target.name + '.download').exists())

    def test_retry_follows_redistribution_only_for_the_same_published_bytes(self):
        asset = dict(id=1, name='states.23Oct2026.csv.7z', size=100, state='uploaded',
                     digest='sha256:' + 'a' * 64)
        missing = subprocess.CalledProcessError(1, 'gh', stderr=b'gh: Not Found (HTTP 404)')
        github = Mock()
        for changed in (False, True):
            with self.subTest(changed=changed):
                candidate = dict(asset, id=2, digest='sha256:' + ('b' if changed else 'a') * 64)
                github.download.reset_mock()
                github.download.side_effect = [missing, None]
                with patch.object(daily, 'release_inventory', return_value=[{'assets': [candidate]}]):
                    if changed:
                        with self.assertRaises(subprocess.CalledProcessError):
                            daily.download_prerequisite(github, asset, Path('target'))
                        self.assertEqual(github.download.call_count, 1)
                    else:
                        daily.download_prerequisite(github, asset, Path('target'))
                        self.assertEqual(github.download.call_args.args[0], candidate)


@unittest.skipUnless(shutil.which('jq'), 'jq is required for the runner preflight')
class PublishedPreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'outputs'
        self.calls = self.root / 'calls'
        self.pages = self.root / 'pages.json'
        self.script = Path(__file__).resolve().parents[1] / 'utils/check_published_component.sh'
        gh = self.root / 'gh'
        gh.write_text('''#!/bin/bash
printf '%s\\n' "$*" >> "$TEST_CALLS"
if [[ "${TEST_API_FAILURE:-}" == true ]]; then exit 1; fi
cat "$TEST_PAGES"
''')
        gh.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{self.root}:{os.environ["PATH"]}',
                        TEST_CALLS=str(self.calls), TEST_PAGES=str(self.pages),
                        GITHUB_REPOSITORY='owner/repo', GITHUB_OUTPUT=str(self.output),
                        LGD_COMPONENT='STATES', LGD_COLLECTION_DATE='23Oct2026',
                        LGD_ASSIGNMENT=json.dumps(dict(release_id=7,
                            asset_name='states.23Oct2026.csv.7z')))
        self.asset = dict(id=17, name='states.23Oct2026.csv.7z', state='uploaded', size=100,
                          digest='sha256:' + 'a' * 64)

    def check(self, pages, **env):
        self.pages.write_text(json.dumps(pages))
        return subprocess.run(['bash', str(self.script)], env=dict(self.env, **env),
                              capture_output=True, text=True)

    def test_completed_asset_on_later_page_emits_the_normal_dependency_receipt(self):
        result = self.check([[dict(self.asset, name='states.22Oct2026.csv.7z')], [self.asset]])
        self.assertEqual(result.returncode, 0, result.stderr)
        key, value = self.output.read_text().strip().split('=', 1)
        self.assertEqual(key, 'published')
        self.assertEqual(json.loads(value), daily.published_receipt(
            Mock(), 'STATES', '23Oct2026', self.asset))
        self.assertEqual(self.calls.read_text().strip(),
                         'api repos/owner/repo/releases/7/assets?per_page=100 --paginate --slurp')

    def test_missing_placeholder_and_legacy_assets_continue_without_receipt(self):
        for assets in ([], [dict(self.asset, name='states.22Oct2026.csv.7z')],
                       [dict(self.asset, state='starter', size=0)],
                       [dict(self.asset, digest=None)]):
            with self.subTest(assets=assets):
                result = self.check([assets])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(self.output.exists())

    def test_partial_ambiguous_or_failed_api_results_never_emit_success(self):
        for assets, env in (([dict(self.asset, state='starter')], {}),
                            ([dict(self.asset, size=0)], {}),
                            ([self.asset, self.asset], {}),
                            ([self.asset], {'TEST_API_FAILURE': 'true'}),
                            ([self.asset], {'LGD_COLLECTION_DATE': '24Oct2026'})):
            with self.subTest(assets=assets, env=env):
                result = self.check([assets], **env)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())

    def test_transactions_always_take_the_cumulative_update_path(self):
        result = self.check([[self.asset]], LGD_COMPONENT='TRANSACTIONS')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.calls.exists())

    def test_reused_receipt_gates_every_expensive_step_and_remains_a_job_output(self):
        workflow = generator.WORKFLOW.with_name('lgd_component.yml').read_text()
        steps = workflow.split('  Component:\n', 1)[1].split('      - ')[1:]
        preflight = next(i for i, step in enumerate(steps) if 'id: published\n' in step)
        for step in steps[preflight + 1:]:
            self.assertIn("steps.published.outputs.published == ''", step)
        self.assertIn('published: ${{ steps.published.outputs.published || steps.run.outputs.published }}',
                      workflow)
        self.assertNotIn('uv ', steps[preflight])
        self.assertNotIn('python', steps[preflight])


@unittest.skipUnless(shutil.which('7z'), '7z is required for release handoffs')
class DailyHandoffTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        previous = Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, previous)
        env = patch.dict(os.environ, LGD_COLLECTION_DATE='23Oct2026', GITHUB_OUTPUT=str(Path('outputs').resolve()))
        env.start()
        self.addCleanup(env.stop)
        Path('data/raw/23Oct2026').mkdir(parents=True)
        self.remote = FakeGitHub()
        self.assignment = dict(release_id=1, release_tag='lgd-latest')
        self.state = Dataset('STATES')
        self.village = Dataset('VILLAGES', ['STATES'])
        self.items = dict(STATES=self.state, VILLAGES=self.village)
        mock = patch.object(daily, 'downloaders', return_value=self.items)
        mock.start()
        self.addCleanup(mock.stop)
        run = subprocess.run

        def quiet(*args, **kwargs):
            if args[0][0] == '7z' and 'stdout' not in kwargs and not kwargs.get('capture_output'):
                kwargs['stdout'] = subprocess.DEVNULL
            return run(*args, **kwargs)

        mock = patch.object(daily.subprocess, 'run', side_effect=quiet)
        mock.start()
        self.addCleanup(mock.stop)

    def scrape(self, component='STATES'):
        Path(self.items[component].get_filename()).write_text('Code,Name\n1,Example\n')
        Path('status.json').write_text(json.dumps({'done': [component], 'error': [], 'left': []}))
        return 0

    def publish_state(self):
        with patch.object(daily, 'run_bounded', side_effect=lambda command: self.scrape()):
            self.assertEqual(daily.run_component(self.remote, 'STATES', self.assignment, {}), 0)
        receipt = json.loads(Path('outputs').read_text().strip().split('=', 1)[1])
        return {'STATES': {'result': 'success', 'outputs': {'published': json.dumps(receipt)}}}

    def test_parent_upload_then_dependent_download_preserves_published_bytes(self):
        needs = self.publish_state()
        published = Path(self.state.get_filename()).read_bytes()
        Path(self.state.get_filename()).write_bytes(b'stale cached prerequisite')
        daily.restore_dependencies(self.remote, 'VILLAGES', self.items, needs, '23Oct2026')
        self.assertEqual(Path(self.state.get_filename()).read_bytes(), published)
        self.assertEqual(self.remote.events, [('upload', 'states.23Oct2026.csv.7z'),
                                             ('download', 'states.23Oct2026.csv.7z')])

    def test_rerun_reuses_completed_upload_without_querying_lgd(self):
        self.publish_state()
        with patch.object(daily, 'run_bounded') as scrape, patch.object(daily, 'restore_dependencies') as restore:
            daily.run_component(self.remote, 'STATES', self.assignment, {})
            scrape.assert_not_called()
            restore.assert_not_called()
        self.assertEqual(len(self.remote.events), 1)

    def test_failed_or_incomplete_scrape_does_not_publish(self):
        for code in (1, 124):
            with patch.object(daily, 'run_bounded', return_value=code):
                self.assertEqual(daily.run_component(self.remote, 'STATES', self.assignment, {}), code)
        with patch.object(daily, 'run_bounded', side_effect=lambda command: self.scrape('VILLAGES')):
            with self.assertRaisesRegex(ValueError, 'complete report'):
                daily.run_component(self.remote, 'STATES', self.assignment, {})
        self.assertEqual(self.remote.events, [])
        self.assertFalse(Path('outputs').exists())

    def test_upload_failure_leaves_csv_for_retry_and_no_success_output(self):
        self.remote.fail_upload = True
        with patch.object(daily, 'run_bounded', side_effect=lambda command: self.scrape()):
            with self.assertRaisesRegex(RuntimeError, 'upload failed'):
                daily.run_component(self.remote, 'STATES', self.assignment, {})
        self.assertTrue(Path(self.state.get_filename()).exists())
        self.assertFalse(Path('outputs').exists())

    def test_dependency_failure_date_and_checksum_cannot_be_ignored(self):
        needs = self.publish_state()
        receipt = json.loads(needs['STATES']['outputs']['published'])
        for replacement in ({'date': '22Oct2026'}, {'component': 'DISTRICTS'},
                            {'asset': dict(receipt['asset'], digest='sha256:' + '0' * 64)}):
            with self.subTest(replacement=replacement):
                changed = dict(receipt, **replacement)
                needs['STATES']['outputs']['published'] = json.dumps(changed)
                with self.assertRaises(ValueError):
                    daily.restore_dependencies(self.remote, 'VILLAGES', self.items, needs, '23Oct2026')
        needs['STATES']['result'] = 'failure'
        with self.assertRaisesRegex(ValueError, 'did not succeed'):
            daily.restore_dependencies(self.remote, 'VILLAGES', self.items, needs, '23Oct2026')

    def test_extraction_rejects_wrong_member_and_preserves_old_csv_on_failure(self):
        self.publish_state()
        archive = Path('archive.7z')
        archive.write_bytes(next(iter(self.remote.files.values())))
        target = Path(self.state.get_filename())
        old = target.read_bytes()
        with self.assertRaises(ValueError):
            daily.extract_csv(archive, 'wrong.csv', target)
        self.assertEqual(target.read_bytes(), old)
        run = subprocess.run

        def fail_extract(command, **kwargs):
            if command[:3] == ['7z', 'e', '-so']:
                kwargs['stdout'].write(b'partial')
                raise subprocess.CalledProcessError(2, command)
            return run(command, **kwargs)

        with patch.object(daily.subprocess, 'run', side_effect=fail_extract):
            with self.assertRaises(subprocess.CalledProcessError):
                daily.extract_csv(archive, 'states.23Oct2026.csv', target)
        self.assertEqual(target.read_bytes(), old)
        self.assertFalse(target.with_suffix('.csv.tmp').exists())

    def test_transaction_retry_seeds_published_history_and_preserves_range_checkpoints(self):
        history = Path('data/raw/transactions')
        history.mkdir()
        previous = history / 'combined.csv'
        coverage = history / 'dates_covered.txt'
        previous.write_text('stale local cumulative report')
        coverage.write_text('stale coverage')
        partial = history / 'parts/complete-range.csv'
        partial.parent.mkdir()
        partial.write_text('already fetched range')
        daily_path = Path('data/raw/23Oct2026/transactions.csv')
        daily_path.write_text('stale daily aggregate')
        seed = Path('transactions.csv')
        seed.write_text('ID,Description\n1,Historical event\n2,Recent event\n')
        packed = Path('transactions.csv.7z')
        subprocess.run(['7z', 'a', str(packed), str(seed)], check=True)
        self.remote.add(packed.name, packed.read_bytes())
        self.remote.add('transactions_dates_covered.txt', b'2026-10-21\n2026-10-22\n')
        downloader = SimpleNamespace(history_dir=history, previous_file=previous,
                                     coverage_file=coverage, get_filename=lambda: str(daily_path))
        daily.seed_transactions(self.remote, 1, downloader)
        self.assertEqual(previous.read_bytes(), seed.read_bytes())
        self.assertEqual(coverage.read_text(), '2026-10-21\n2026-10-22\n')
        self.assertEqual(partial.read_text(), 'already fetched range')
        self.assertFalse(daily_path.exists())

    def test_transaction_coverage_download_failure_does_not_change_local_history(self):
        history = Path('data/raw/transactions')
        history.mkdir()
        previous = history / 'combined.csv'
        coverage = history / 'dates_covered.txt'
        previous.write_text('existing history')
        coverage.write_text('existing coverage')
        downloader = SimpleNamespace(history_dir=history, previous_file=previous, coverage_file=coverage)
        self.remote.add('transactions.csv.7z', b'archive contents')
        self.remote.add('transactions_dates_covered.txt', b'coverage contents')
        real_download = self.remote.download

        def fail_coverage(asset, path):
            if asset['name'].endswith('.txt'):
                raise RuntimeError('coverage unavailable')
            real_download(asset, path)

        with patch.object(self.remote, 'download', side_effect=fail_coverage):
            with self.assertRaisesRegex(RuntimeError, 'coverage unavailable'):
                daily.seed_transactions(self.remote, 1, downloader)
        self.assertEqual(previous.read_text(), 'existing history')
        self.assertEqual(coverage.read_text(), 'existing coverage')


if __name__ == '__main__':
    unittest.main()
