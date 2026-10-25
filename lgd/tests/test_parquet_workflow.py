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

    def require_release(self, tag):
        if tag not in self.listed:
            raise ValueError(f'Missing release {tag}; create it manually before publishing')
        if self.listed[tag].get('draft') or self.listed[tag].get('immutable'):
            raise ValueError('Publication release must be public and accept new assets')
        return self.listed[tag]

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

    def put(self, tag, path, *, mutable=False):
        self.require_release(tag)
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
        self.client.listed[RELEASE] = dict(tag_name=RELEASE, draft=False)

    def source(self, day='23Oct2026', payload=b'archive', dataset='states', tag='lgd-latest'):
        return self.client.add(tag, f'{dataset}.{day}.csv.7z', payload)

    def complete(self, plan, dataset='states'):
        task = plan['tasks'][dataset]
        path = self.root/task['parquet_name']
        path.write_bytes(b'parquet '+task['identity'].encode())
        ref = self.client.put(task['release'], path)
        manifest = dict(dataset=dataset, identity=task['identity'], source=task['source'],
                        converter=plan['converter'], representation='snapshot', coverage=None,
                        daily=dict(file=ref, observed_on=task['source']['observed_on'], rows=1))
        path = self.root/task['manifest_name']
        path.write_bytes(encoded(manifest))
        self.client.put(task['release'], path)

    def publish_first(self):
        self.source()
        plan = flow.prepare(self.client, ['states'], COMMIT)
        self.complete(plan)
        return flow.publish(self.client, plan, self.root)

    def test_ward_reference_is_dated_pinned_and_part_of_conversion_identity(self):
        self.source(dataset='pri_local_body_wards')
        old=self.source(day='22Oct2026',dataset='pri_local_bodies',payload=b'old')
        self.source(day='24Oct2026',dataset='pri_local_bodies',payload=b'future')
        plan=flow.prepare(self.client,['pri_local_body_wards'],COMMIT)
        task=plan['tasks']['pri_local_body_wards']
        self.assertEqual(task['source']['name_reference']['asset']['id'],old['id'])
        self.source(day='23Oct2026',dataset='pri_local_bodies',payload=b'current')
        later=flow.prepare(self.client,['pri_local_body_wards'],COMMIT)
        self.assertNotEqual(task['identity'],later['tasks']['pri_local_body_wards']['identity'])
        self.source(day='22Oct2026',dataset='pri_local_bodies',payload=b'replacement')
        with self.assertRaisesRegex(ValueError,'Source changed'):
            flow.check_sources(self.client,task['source'])

    def test_discrepancy_outputs_reserve_a_third_release_asset(self):
        for dataset in flow.DISCREPANCY_DATASETS:
            with self.subTest(dataset=dataset):
                self.client.data[RELEASE] = {str(i): {} for i in range(977)}
                with self.assertRaisesRegex(ValueError, 'Insufficient release capacity'):
                    flow.allocate(self.client, [dataset])  # Three files plus the index.
                self.client.data[RELEASE].pop('976')
                self.assertEqual(flow.allocate(self.client, [dataset]),
                                 {dataset: RELEASE, '_index': RELEASE})

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

    def test_retry_can_finish_a_partially_published_plan_without_overwriting_its_index(self):
        self.source()
        self.source(dataset='districts')
        plan = flow.prepare(self.client, ['states', 'districts'], COMMIT)
        self.complete(plan, 'states')
        first = flow.publish(self.client, plan, self.root)
        self.assertEqual(first['datasets']['districts']['outcome']['status'], 'failed')
        self.complete(plan, 'districts')
        second = flow.publish(self.client, plan, self.root)
        self.assertEqual(second['datasets']['districts']['outcome']['status'], 'updated')
        self.assertNotEqual(first['immutable_url'], second['immutable_url'])
        self.assertEqual(second['previous_index_url'], first['immutable_url'])
        before = len(self.client.uploads)
        self.assertEqual(flow.publish(self.client, plan, self.root), second)
        self.assertEqual(len(self.client.uploads), before)

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
        result = flow.recover(self.client, self.root)
        self.assertEqual(result['datasets']['states']['daily']['observed_on'], '2026-10-24')

    def test_capacity_rollover_preserves_latest_pointer_release(self):
        self.client.listed[RELEASE] = dict(draft=False)
        self.client.data[RELEASE] = {str(i): {} for i in range(979)}
        with self.assertRaisesRegex(ValueError, 'create lgd-parquet-extra-0001 manually'):
            flow.allocate(self.client, ['states', 'villages'])
        self.assertEqual(set(self.client.listed), {RELEASE})
        self.client.listed['lgd-parquet-extra-0001'] = dict(draft=False)
        allocated = flow.allocate(self.client, ['states', 'villages'])
        self.assertEqual(allocated['states'], 'lgd-parquet-extra-0001')
        self.assertEqual(allocated['villages'], 'lgd-parquet-extra-0001')
        self.assertEqual(allocated['_index'], RELEASE)

    def test_prepare_requires_manual_destination_before_discovering_sources(self):
        self.client.listed.pop(RELEASE)
        with patch.object(flow, 'inventory', side_effect=AssertionError('Too early for discovery')):
            with self.assertRaisesRegex(ValueError, 'create it manually'):
                flow.prepare(self.client, ['states'], COMMIT)

    def test_transport_reports_missing_release_without_attempting_creation(self):
        client = object.__new__(GitHub)
        client.listed, client.inventory = {}, {}
        error = subprocess.CalledProcessError(1, ['gh', 'api'], stderr='gh: Not Found (HTTP 404)')
        with patch.object(client, 'api', side_effect=error) as api:
            with self.assertRaisesRegex(ValueError, 'create it manually'):
                client.require_release(RELEASE)
        api.assert_called_once_with(f'releases/tags/{RELEASE}')

    def test_transport_reads_manual_release_directly_when_listing_lags(self):
        client = object.__new__(GitHub)
        client.listed, client.inventory = {}, {}
        release = dict(id=42, tag_name=RELEASE, draft=False, immutable=False)
        with patch.object(client, 'api', return_value=release) as api, \
                patch.object(client, 'refresh', side_effect=AssertionError('Must not re-list')):
            self.assertEqual(client.require_release(RELEASE), release)
            self.assertEqual(client.require_release(RELEASE), release)
        api.assert_called_once_with(f'releases/tags/{RELEASE}')
        self.assertEqual(client.listed[RELEASE], release)

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
        with patch.object(client, 'require_release'), \
                patch.object(client, 'release_assets', return_value={path.name: existing}), \
                patch.object(client, 'upload') as upload:
            self.assertEqual(client.put(RELEASE, path), ref)
            upload.assert_not_called()
            path.write_bytes(b'different')
            with self.assertRaises(ValueError):
                client.put(RELEASE, path)
            with self.assertRaisesRegex(ValueError, 'Only discovery'):
                client.put(RELEASE, path, mutable=True)
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
    def test_real_ward_worker_publishes_reference_and_original_discrepancy_rows(self):
        import csv
        def row(dataset,**kwargs):
            return {name: ('1' if kind=='INTEGER' or name.endswith('_code') else 'Label')
                    for _,name,kind,_ in flow.SCHEMAS[dataset]} | kwargs
        a=row('pri_local_body_wards',ward_code='100',local_body_code='10',local_body_name='First')
        ignored=dict(a,ward_code='624571',local_body_code='6004',state_code='28')
        reports={
            'pri_local_bodies':[row('pri_local_bodies',local_body_code='10',parent_local_body_code='',
                                   local_body_name='Preferred',local_body_type_code='1')],
            'pri_local_body_wards':[a,dict(a,local_body_name='Second'),a,ignored,dict(ignored,state_code='36')]}
        for dataset,rows in reports.items():
            path=self.root/f'{dataset}.30Jan2022.csv'
            fields=flow.SCHEMAS[dataset]
            with path.open('w',newline='') as f:
                writer=csv.writer(f);writer.writerow(['S.No.']+[field[3] for field in fields])
                writer.writerows([[i]+[r[field[1]] for field in fields] for i,r in enumerate(rows,1)])
            archive=path.with_suffix('.csv.7z')
            subprocess.run(['7z','a',str(archive),path.name],cwd=self.root,check=True,capture_output=True)
            self.source(day='30Jan2022',dataset=dataset,payload=archive.read_bytes())
        plan=flow.prepare(self.client,['pri_local_body_wards'],COMMIT)
        flow.worker(self.client,plan,'pri_local_body_wards',self.root/'work')
        manifest,_=flow.candidate(self.client,plan,'pri_local_body_wards')
        self.assertEqual(manifest['daily']['rows'],1)
        receipt=manifest['conversion']
        self.assertEqual((receipt['ignored_source_rows'],receipt['collapsed_rows']),(2,2))
        self.assertEqual(receipt['discrepancy_evidence']['rows'],4)
        self.assertNotIn('path',receipt['name_reference'])
        self.assertEqual(receipt['name_reference']['observed_on'],'2022-01-30')
        flow.publish(self.client,plan,self.root)
        tag,name=location(self.client.repo,receipt['discrepancy_evidence']['file'])
        self.client.data[tag].pop(name)
        retry=flow.prepare(self.client,['pri_local_body_wards'],COMMIT)
        self.assertEqual(retry['outcomes']['pri_local_body_wards']['status'],'blocked')
        self.assertEqual(list((self.root/'work').iterdir()),[])

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
