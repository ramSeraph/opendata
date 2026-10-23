"""Daily publication, retries and failure recovery without network side effects."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from utils import parquet_workflow as flow
from utils.parquet_release import GitHub, RELEASE, asset_ref, encoded, location


COMMIT = 'a' * 40


class FakeGitHub:
    def __init__(self):
        self.repo = 'test/repo'
        self.listed, self.data, self.payloads, self.uploads = {}, {}, {}, []
        self.fail_pointer = False

    def add(self, tag, name, payload, updated='2026-10-23T10:00:00Z'):
        self.listed.setdefault(tag, dict(tag_name=tag, draft=False))
        asset = dict(id=len(self.payloads)+1, name=name, state='uploaded', size=len(payload),
                     digest='sha256:'+hashlib.sha256(payload).hexdigest(), updated_at=updated,
                     created_at=updated,
                     browser_download_url=f'https://github.com/{self.repo}/releases/download/{tag}/{name}')
        self.data.setdefault(tag, {})[name] = asset
        self.payloads[asset['id']] = payload
        return asset

    def release_assets(self, tag, **kwargs):
        return self.data.get(tag, {})

    def read_json(self, asset):
        return json.loads(self.payloads[asset['id']])

    def read_index(self):
        assets = self.release_assets(RELEASE)
        if 'metadata.json' in assets:
            return self.read_json(assets['metadata.json'])
        if any(name.startswith('metadata.') for name in assets):
            raise ValueError('Discovery metadata is missing; run publication recovery')
        return None

    def download(self, asset, destination):
        Path(destination).write_bytes(self.payloads[asset['id']])

    def verify_ref(self, ref):
        tag, name = location(self.repo, ref)
        asset = self.release_assets(tag).get(name)
        if not asset or (asset['size'], asset['digest']) != (ref['size'], 'sha256:'+ref['sha256']):
            raise ValueError('Reference checksum differs or asset is missing')
        return asset

    def put(self, tag, path, commit, *, mutable=False):
        path = Path(path)
        ref = asset_ref(self.repo, tag, path)
        if path.name in self.release_assets(tag) and not mutable:
            self.verify_ref(ref)
            return ref
        if mutable and path.name == 'metadata.json' and self.fail_pointer:
            self.data.get(tag, {}).pop(path.name, None)
            raise ValueError('Simulated interruption replacing metadata.json')
        self.add(tag, path.name, path.read_bytes())
        self.uploads.append((tag, path.name, mutable))
        return ref


class ParquetWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = FakeGitHub()

    def source(self, day='23Oct2026', payload=b'archive', dataset='states', tag='lgd-latest'):
        return self.client.add(tag, f'{dataset}.{day}.csv.7z', payload)

    def complete(self, plan, dataset='states'):
        task = plan['tasks'][dataset]
        path = self.root/task['parquet_name']
        path.write_bytes(b'parquet '+task['identity'].encode())
        ref = self.client.put(task['release'], path, COMMIT)
        manifest = dict(dataset=dataset, identity=task['identity'], source=task['source'],
                        converter=plan['converter'], representation='snapshot', coverage=None,
                        daily=dict(file=ref, observed_on=task['source']['observed_on'], rows=1))
        path = self.root/task['manifest_name']
        path.write_bytes(encoded(manifest))
        self.client.put(task['release'], path, COMMIT)

    def publish_first(self):
        self.source()
        plan = flow.prepare(self.client, ['states'], COMMIT)
        self.complete(plan)
        return flow.publish(self.client, plan, self.root)

    def test_publish_then_noop_before_conversion_and_keep_old_assets(self):
        first = self.publish_first()
        plan = flow.prepare(self.client, ['states'], COMMIT)
        self.assertFalse(plan['tasks'])
        self.assertEqual(plan['outcomes']['states']['status'], 'unchanged')
        second = flow.publish(self.client, plan, self.root)
        self.assertEqual(first['datasets']['states']['daily'], second['datasets']['states']['daily'])
        before = len(self.client.uploads)
        flow.publish(self.client, plan, self.root)
        self.assertEqual(len(self.client.uploads), before)
        self.client.verify_ref(first['datasets']['states']['daily']['file'])

    def test_failed_worker_keeps_previous_date_while_other_worker_advances(self):
        old = self.publish_first()
        self.source('24Oct2026')
        self.source('24Oct2026', dataset='districts')
        plan = flow.prepare(self.client, ['states', 'districts'], COMMIT)
        self.complete(plan, 'districts')
        result = flow.publish(self.client, plan, self.root)
        self.assertEqual(result['datasets']['states']['daily'], old['datasets']['states']['daily'])
        self.assertEqual(result['datasets']['states']['outcome']['status'], 'failed')
        self.assertEqual(result['datasets']['districts']['daily']['observed_on'], '2026-10-24')

    def test_absent_and_older_sources_do_not_advance_or_delete(self):
        old = self.publish_first()
        self.client.data['lgd-latest'].clear()
        plan = flow.prepare(self.client, ['states', 'villages'], COMMIT)
        result = flow.publish(self.client, plan, self.root)
        self.assertEqual(result['datasets']['states']['daily'], old['datasets']['states']['daily'])
        self.assertNotIn('daily', result['datasets']['villages'])
        self.source('22Oct2026')
        plan = flow.prepare(self.client, ['states'], COMMIT)
        self.assertFalse(plan['tasks'])

    def test_same_day_correction_and_converter_change_get_new_names(self):
        self.source()
        first = flow.prepare(self.client, ['states'], COMMIT)
        self.source(payload=b'corrected archive')
        second = flow.prepare(self.client, ['states'], COMMIT)
        self.assertNotEqual(first['tasks']['states']['parquet_name'], second['tasks']['states']['parquet_name'])
        with patch.object(flow, 'converter_version', return_value={'sha256': 'b'*64, 'dependency': flow.DEPENDENCY}):
            third = flow.prepare(self.client, ['states'], COMMIT)
        self.assertNotEqual(second['tasks']['states']['parquet_name'], third['tasks']['states']['parquet_name'])

    def test_duplicate_conflicting_sources_block_only_that_dataset(self):
        self.source()
        self.source(payload=b'different', tag='lgd-latest-extra1')
        self.source(dataset='districts')
        plan = flow.prepare(self.client, ['states', 'districts'], COMMIT)
        self.assertEqual(set(plan['tasks']), {'districts'})
        self.assertEqual(plan['outcomes']['states']['status'], 'blocked')

    def test_retry_reuses_candidate_and_rejects_source_replacement(self):
        self.source()
        plan = flow.prepare(self.client, ['states'], COMMIT)
        self.complete(plan)
        with patch('parquet.convert.convert', side_effect=AssertionError('Must not reconvert')):
            flow.worker(self.client, plan, 'states', self.root)
        source = plan['tasks']['states']['source']
        self.source(payload=b'new bytes')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            flow.check_sources(self.client, source)

    def test_stale_parent_cannot_replace_newer_publication(self):
        self.source()
        old = flow.prepare(self.client, ['states'], COMMIT)
        new = flow.prepare(self.client, ['states'], COMMIT)
        self.complete(new)
        flow.publish(self.client, new, self.root)
        with self.assertRaisesRegex(ValueError, 'parent changed'):
            flow.publish(self.client, old, self.root)

    def test_recovery_after_pointer_replacement_interrupts(self):
        old = self.publish_first()
        self.source('24Oct2026')
        plan = flow.prepare(self.client, ['states'], COMMIT)
        self.complete(plan)
        self.client.fail_pointer = True
        with self.assertRaisesRegex(ValueError, 'interruption'):
            flow.publish(self.client, plan, self.root)
        self.assertEqual(self.client.read_json(self.client.data[RELEASE]['metadata.previous.json']), old)
        self.client.fail_pointer = False
        # Both indexes can have the same upload timestamp; asset IDs break ties.
        result = flow.recover(self.client, self.root, COMMIT)
        self.assertEqual(result['datasets']['states']['daily']['observed_on'], '2026-10-24')

    def test_capacity_rollover_preserves_latest_pointer_release(self):
        self.client.listed[RELEASE] = dict(draft=False)
        self.client.data[RELEASE] = {str(i): {} for i in range(979)}
        allocated = flow.allocate(self.client, ['states', 'villages'])
        self.assertEqual(allocated['states'], 'lgd-parquet-extra-0001')
        self.assertEqual(allocated['villages'], 'lgd-parquet-extra-0001')
        self.assertEqual(allocated['_index'], RELEASE)

    def test_event_source_requires_coverage_and_does_not_invent_observation_date(self):
        self.client.add('lgd-latest', 'transactions.csv.7z', b'events')
        plan = flow.prepare(self.client, ['transactions'], COMMIT)
        self.assertEqual(plan['outcomes']['transactions']['status'], 'blocked')
        self.client.add('lgd-latest', 'transactions_dates_covered.txt', b'2026-10-23\n')
        plan = flow.prepare(self.client, ['transactions'], COMMIT)
        self.assertIsNone(plan['tasks']['transactions']['source']['observed_on'])

    def test_event_coverage_rejects_mismatched_ledger(self):
        import duckdb
        path = self.root/'events.parquet'
        ledger = self.root/'coverage.txt'
        with duckdb.connect(config={'threads': 1}) as connection:
            connection.execute("COPY (SELECT DATE '2026-10-23' AS transaction_date) TO ? (FORMAT PARQUET)", [str(path)])
            ledger.write_text('2026-10-22\n')
            with self.assertRaisesRegex(ValueError, 'outside'):
                flow.event_coverage(connection, path, 'transactions', ledger)
            ledger.write_text('2026-10-21\n2026-10-23\n')
            coverage = flow.event_coverage(connection, path, 'transactions', ledger)
            self.assertEqual(coverage['collected_dates'], ['2026-10-21', '2026-10-23'])

    def test_source_replacement_after_upload_is_not_advertised(self):
        self.source()
        plan = flow.prepare(self.client, ['states'], COMMIT)
        self.complete(plan)
        self.source(payload=b'corrected source')
        result = flow.publish(self.client, plan, self.root)
        self.assertEqual(result['datasets']['states']['outcome']['status'], 'failed')
        self.assertNotIn('daily', result['datasets']['states'])

    def test_transport_refuses_to_clobber_different_immutable_bytes(self):
        client = object.__new__(GitHub)
        client.repo = 'test/repo'
        client.inventory = {}
        path = self.root/'states.2026-10-23.test.parquet'
        path.write_bytes(b'original')
        ref = asset_ref(client.repo, RELEASE, path)
        existing = dict(state='uploaded', size=ref['size'], digest='sha256:'+ref['sha256'])
        with patch.object(client, 'ensure_release'), \
                patch.object(client, 'release_assets', return_value={path.name: existing}), \
                patch.object(client, 'upload') as upload:
            self.assertEqual(client.put(RELEASE, path, COMMIT), ref)
            upload.assert_not_called()
            path.write_bytes(b'different')
            with self.assertRaises(ValueError):
                client.put(RELEASE, path, COMMIT)
            with self.assertRaisesRegex(ValueError, 'Only discovery'):
                client.put(RELEASE, path, COMMIT, mutable=True)
            upload.assert_not_called()

    def test_discovery_imports_without_converter_or_history_dependencies(self):
        import sys
        package = Path(__file__).resolve().parents[1]
        script = '''
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('duckdb', 'history', 'pyiceberg', 'pyarrow', 'requests'):
            raise ImportError('Preparation must not import ' + fullname)
sys.meta_path.insert(0, Block())
sys.path.insert(0, sys.argv[1])
from utils.parquet_workflow import SCHEMAS, converter_version
assert len(SCHEMAS) == 39
assert converter_version()['dependency'] == 'duckdb==2.0.0'
'''
        subprocess.run([sys.executable, '-I', '-c', script, str(package)], check=True)

    @unittest.skipUnless(shutil.which('7z'), '7z required')
    def test_real_converter_worker_uploads_valid_manifest_and_cleans_scratch(self):
        csv = self.root/'states.23Oct2026.csv'
        csv.write_text('S.No.,State Code,State Version,State Name (In English),State Name (In Local),'
                       'Census 2001 Code,Census 2011 Code,State or UT\n'
                       '1,01,2,Name,,01,01,State\n')
        archive = csv.with_suffix('.csv.7z')
        subprocess.run(['7z', 'a', str(archive), csv.name], cwd=self.root, check=True, capture_output=True)
        self.source(payload=archive.read_bytes())
        plan = flow.prepare(self.client, ['states'], COMMIT)
        flow.worker(self.client, plan, 'states', self.root/'work')
        manifest, _ = flow.candidate(self.client, plan, 'states')
        self.assertEqual(manifest['daily']['rows'], 1)
        self.assertEqual(manifest['csv_sha256'], hashlib.sha256(csv.read_bytes()).hexdigest())
        self.assertEqual(list((self.root/'work').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
