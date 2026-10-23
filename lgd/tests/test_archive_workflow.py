import json
import os
import shutil
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests import test_archive as fixtures
from utils import archive_prev_month as archive
from utils import archive_workflow as workflow


@unittest.skipUnless(shutil.which('7z'), '7z is required to exercise actual archive publication')
class ArchiveWorkflowTests(unittest.TestCase):
    # Reuse the real-7z/in-memory-release fixture, without duplicating its tests.
    add_daily = fixtures.ArchiveTests.add_daily
    make_archive = fixtures.ArchiveTests.make_archive
    assert_originals_retained = fixtures.ArchiveTests.assert_originals_retained

    def setUp(self):
        fixtures.ArchiveTests.setUp(self)
        env = patch.dict(os.environ, GITHUB_RUN_ID='123', GITHUB_SHA='revision')
        env.start()
        self.addCleanup(env.stop)
        self.item = dict(prefix='states', month='Jan2026', dates=['01Jan2026', '02Jan2026'],
                         target='lgd-archive', published=None,
                         sources={file.name + '.7z': 'lgd-latest' for file in self.files})

    def build(self):
        with self.remote.installed():
            workflow.build(self.item)
        return json.loads(Path('archive-receipt.json').read_text())

    def finalize(self, receipt):
        with self.remote.installed(), patch.object(archive, 'refresh_indexes'):
            workflow.finalize(self.item, receipt)

    def test_workers_publish_without_deleting_or_updating_shared_mapping(self):
        receipt = self.build()
        self.assert_originals_retained()
        mapping = json.loads(self.remote.assets['lgd-archive', 'archive_mapping.json'][0])
        self.assertEqual(mapping, self.initial_mapping)
        self.assertEqual(receipt['item'], self.item)
        self.assertIn(('lgd-archive', 'states.Jan2026.7z'), self.remote.assets)
        self.finalize(receipt)
        mapping = json.loads(self.remote.assets['lgd-archive', 'archive_mapping.json'][0])
        self.assertEqual(set(mapping['states']), {'31Dec2025', '01Jan2026', '02Jan2026'})
        self.assertEqual(mapping['districts'], self.initial_mapping['districts'])
        self.assertFalse(any(tag == 'lgd-latest' for tag, name in self.remote.assets))
        events = self.remote.events
        mapping_upload = events.index(('upload', 'archive_mapping.json'))
        first_delete = next(i for i, event in enumerate(events) if event[0] == 'delete')
        self.assertLess(mapping_upload, first_delete)
        # A modern asset's digest lets the coordinator avoid a second download.
        self.assertNotIn(('download', 'states.Jan2026.7z'), events)

    def test_changed_published_asset_or_receipt_preserves_all_daily_data(self):
        receipt = self.build()
        for override in ({'digest': 'sha256:' + '0' * 64}, {'size': 1},
                         {'apiUrl': 'https://api.github.com/assets/replaced'}, {'state': 'starter'}):
            with self.subTest(override=override):
                self.remote.overrides['states.Jan2026.7z'] = override
                with self.assertRaises(ValueError):
                    self.finalize(receipt)
                self.assert_originals_retained()
        self.remote.overrides.clear()
        for replacement in ({'run_id': 'another-run'}, {'item': dict(self.item, dates=['02Jan2026'])},
                            {'name': 'districts.Jan2026.7z'}):
            with self.assertRaises(ValueError):
                self.finalize(dict(receipt, **replacement))
            self.assert_originals_retained()

    def test_mapping_upload_failure_never_authorizes_deletion(self):
        receipt = self.build()
        self.remote.fail_upload = 'archive_mapping.json'
        with self.assertRaises(RuntimeError):
            self.finalize(receipt)
        self.assert_originals_retained()
        self.remote.fail_upload = None
        self.finalize(receipt)
        self.assertFalse(any(tag == 'lgd-latest' for tag, name in self.remote.assets))

    def test_retry_after_partial_deletion_is_idempotent(self):
        receipt = self.build()
        self.remote.fail_delete = self.files[1].name + '.7z'
        with self.assertRaises(RuntimeError):
            self.finalize(receipt)
        self.assertNotIn(('lgd-latest', self.files[0].name + '.7z'), self.remote.assets)
        self.assertIn(('lgd-latest', self.files[1].name + '.7z'), self.remote.assets)
        self.remote.fail_delete = None
        self.finalize(receipt)
        self.finalize(receipt)
        mapping = json.loads(self.remote.assets['lgd-archive', 'archive_mapping.json'][0])
        self.assertEqual(len(mapping['states']), 3)

    def test_retry_reuses_upload_even_if_original_plan_did_not_know_about_it(self):
        self.build()
        self.final.unlink()
        self.build()
        self.assertEqual(self.remote.events.count(('upload', 'states.Jan2026.7z')), 1)
        self.assertIn(('download', 'states.Jan2026.7z'), self.remote.events)
        self.assert_originals_retained()

    def test_legacy_asset_without_digest_is_verified_by_coordinator(self):
        receipt = self.build()
        self.remote.overrides['states.Jan2026.7z'] = {'digest': None}
        self.finalize(receipt)
        self.assertIn(('download', 'states.Jan2026.7z'), self.remote.events)

    def test_parallel_upload_destinations_are_reserved_before_workers_start(self):
        for index in range(988):
            self.remote.add(f'older-{index}', b'old archive')
        self.remote.add('districts.01Jan2026.csv.7z', b'new dataset', release='lgd-latest')
        with self.remote.installed(), patch.object(archive, 'run_external') as create:
            items = workflow.plan_archives('Jan2026')
        self.assertEqual([(item['prefix'], item['target']) for item in items],
                         [('districts', 'lgd-archive'), ('states', 'lgd-archive-extra1')])
        self.assertEqual(create.call_count, 1)

    def test_month_is_based_on_original_run_and_matrix_has_no_parallel_cap(self):
        self.assertEqual(workflow.month_for_run('2026-01-01T00:01:00Z', 1), 'Dec2025')
        self.assertEqual(workflow.month_for_run('2026-01-01T00:01:00Z', 2), 'Nov2025')
        with self.assertRaises(ValueError):
            workflow.month_for_run('2026-01-01T00:01:00Z', 0)
        root = Path(__file__).resolve().parents[2] / '.github/workflows'
        text = (root / 'lgd_archive.yml').read_text()
        self.assertNotIn('max-parallel:', '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('#')))
        self.assertIn('fail-fast: false', text)
        text = (root / 'lgd_archive_component.yml').read_text()
        self.assertIn('group: lgd-archive-metadata\n      queue: max', text)
        self.assertIn('timeout-minutes: 240', text)

    def test_rest_metadata_recovers_checksum_omitted_by_gh_release_view(self):
        url = 'https://api.github.com/repos/example/data/releases/assets/123'
        rest = dict(name='states.Jan2026.7z', url=url, state='uploaded', size=200,
                    digest='sha256:' + 'a' * 64)
        responses = [SimpleNamespace(stdout=json.dumps({'assets': [{'name': rest['name'], 'apiUrl': url}]})),
                     SimpleNamespace(stdout=json.dumps(rest))]
        with patch.object(archive.subprocess, 'run', side_effect=responses) as run:
            metadata = archive.get_release_asset('lgd-archive', rest['name'])
        self.assertEqual(metadata['digest'], rest['digest'])
        self.assertEqual(metadata['apiUrl'], url)
        self.assertEqual(run.call_args_list[-1].args[0], ['gh', 'api', url])


if __name__ == '__main__':
    unittest.main()
