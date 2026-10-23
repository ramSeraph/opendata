"""Reader contracts and failure recovery with synthetic public release files."""

from contextlib import redirect_stderr, redirect_stdout
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import lgd_query
from lgd_query import (DatasetUnavailableError, IntegrityError, MetadataError,
                       ObservationDateError, Release, connect, download,
                       load_manifest, load_release)
from lgd_query import cli


BASE = 'https://example.test/releases/'
INDEX = BASE + 'metadata.json'


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


class PublicFiles:
    def __init__(self):
        self.files = {}
        self.requests = []

    def add(self, name, content):
        url = BASE + name
        self.files[url] = content
        return dict(url=url, size=len(content), sha256=hashlib.sha256(content).hexdigest())

    def open(self, request, **kwargs):
        self.requests.append(request.full_url)
        content = self.files[request.full_url]
        if isinstance(content, Exception):
            raise content
        return io.BytesIO(content)

    def dataset(self, name, content=b'small parquet', *, observed='2026-10-23', status='updated'):
        daily = dict(file=self.add(name+'.parquet', content), rows=2,
                     observed_on=observed, uploaded_at='2026-10-23T15:00:00Z')
        representation = 'events' if observed is None else 'snapshot'
        coverage = dict(first_event_date='2020-01-30', collected_dates=['2020-01-30']) if observed is None else None
        manifest = dict(kind='lgd-daily-parquet', format_version=1, dataset=name, identity=name+'-revision',
                        daily=daily, representation=representation, coverage=coverage,
                        schema=[dict(id=1, name='state_code', type='VARCHAR')])
        return dict(daily=daily, representation=representation, coverage=coverage,
                    identity=manifest['identity'], outcome=dict(status=status),
                    manifest=self.add(name+'.json', encoded(manifest)))

    def index(self, datasets):
        document = dict(kind='lgd-daily-parquet', format_version=1, repository='test/repo',
                        generation='generation-one', published_at='2026-10-23T16:00:00Z',
                        immutable_url=BASE+'metadata.one.json', datasets=datasets)
        self.add('metadata.json', encoded(document))
        return document


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.server = PublicFiles()
        self.document = self.server.index(dict(
            states=self.server.dataset('states'),
            districts=self.server.dataset('districts', observed='2026-10-22', status='failed'),
            transactions=self.server.dataset('transactions', observed=None),
            missing=dict(outcome=dict(status='unavailable', reason='No source'))))
        self.enterContext(patch('lgd_query._http.urlopen', side_effect=self.server.open))

    def test_metadata_is_pinned_with_lazy_manifests_and_actual_dates(self):
        release = load_release(INDEX)
        self.assertEqual(self.server.requests, [INDEX])
        states = release.dataset('states')
        self.assertEqual(states.observed_on, date(2026, 10, 23))
        self.assertEqual(states.rows, 2)
        self.assertEqual(states.parquet.url, BASE+'states.parquet')
        self.server.files[INDEX] = b'new generation'
        self.assertIs(release.dataset('states'), states)
        self.assertEqual(self.server.requests, [INDEX])
        self.assertEqual(load_manifest(states)['schema'][0]['name'], 'state_code')
        self.assertEqual(self.server.requests, [INDEX, BASE+'states.json'])

    def test_missing_failed_and_cumulative_reports_are_distinct(self):
        release = load_release(INDEX)
        self.assertFalse(release.datasets['missing'].available)
        with self.assertRaises(DatasetUnavailableError):
            release.dataset('missing')
        with self.assertRaises(KeyError):
            release.dataset('unknown')
        old = release.dataset('districts')
        self.assertTrue(old.available)
        self.assertEqual((old.status, old.observed_on), ('failed', date(2026, 10, 22)))
        with self.assertRaises(ObservationDateError):
            release.dataset('districts', observed_on='2026-10-23')
        self.assertIs(release.dataset('states', observed_on=date(2026, 10, 23)), release.datasets['states'])
        events = release.dataset('transactions')
        self.assertIsNone(events.observed_on)
        self.assertEqual(events.coverage['collected_dates'], ['2020-01-30'])
        with self.assertRaises(ObservationDateError):
            release.dataset('transactions', observed_on='2026-10-23')

    def test_saved_metadata_and_public_copies_do_not_mutate_resolution(self):
        release = Release.from_dict(self.document)
        self.document['datasets']['states']['daily']['rows'] = 100
        release.metadata['datasets']['states']['daily']['rows'] = 200
        release.dataset('states').metadata['daily']['rows'] = 300
        release.dataset('transactions').coverage['collected_dates'].clear()
        self.assertEqual(release.dataset('states').rows, 2)
        self.assertEqual(Release.from_dict(release.metadata).dataset('states').rows, 2)
        self.assertEqual(release.dataset('transactions').coverage['collected_dates'], ['2020-01-30'])
        with self.assertRaises(TypeError):
            release.datasets['new'] = release.dataset('states')
        self.assertEqual(self.server.requests, [])

    def test_unknown_new_datasets_work_without_a_schema_registry(self):
        document = self.server.index({'future_report': self.server.dataset('future_report')})
        self.assertTrue(Release.from_dict(document).dataset('future_report').available)

    def test_rejects_bad_versions_dates_urls_and_asset_metadata(self):
        modifications = [
            lambda d: d.update(format_version=2),
            lambda d: d.update(kind='history-index'),
            lambda d: d['datasets']['states']['daily'].update(observed_on='20261023'),
            lambda d: d['datasets']['states']['daily'].update(rows=True),
            lambda d: d['datasets']['states']['daily']['file'].update(url='file:///private/data'),
            lambda d: d['datasets']['states']['daily']['file'].update(size=-1),
            lambda d: d['datasets']['states']['daily']['file'].update(sha256='bad'),
            lambda d: d['datasets']['states'].pop('manifest'),
            lambda d: d['datasets']['transactions']['daily'].update(observed_on='2026-10-23'),
        ]
        for modify in modifications:
            with self.subTest(modify=modify):
                document = deepcopy(self.document)
                modify(document)
                with self.assertRaises(MetadataError):
                    Release.from_dict(document)

    def test_manifest_bytes_and_index_agreement_are_verified(self):
        release = load_release(INDEX)
        original = self.server.files[BASE+'states.json']
        self.server.files[BASE+'states.json'] = original+b' '
        with self.assertRaises(IntegrityError):
            load_manifest(release.dataset('states'))
        manifest = json.loads(original)
        manifest['daily']['rows'] = 99
        entry = self.document['datasets']['states']
        entry['manifest'] = self.server.add('states.json', encoded(manifest))
        with self.assertRaisesRegex(MetadataError, 'daily'):
            load_manifest(Release.from_dict(self.document).dataset('states'))

    def test_malformed_asset_urls_are_rejected_before_download(self):
        for url in ('http://[broken', 'https://example.test:bad/file',
                    'https://example.test:65536/file', 'https://example.test/a\nb',
                    ' https://example.test/file', 'https://example.test/a b'):
            with self.subTest(url=url):
                document = deepcopy(self.document)
                document['datasets']['states']['daily']['file']['url'] = url
                with self.assertRaises(MetadataError):
                    Release.from_dict(document)
        self.assertEqual(self.server.requests, [])

    def test_transient_index_404_retries_without_implicit_fallback(self):
        calls = [HTTPError(INDEX, 404, 'replacing', {}, None), io.BytesIO(encoded(self.document))]
        with patch('lgd_query._http.urlopen', side_effect=calls), patch('lgd_query._http.time.sleep'):
            self.assertEqual(load_release(INDEX).generation, 'generation-one')
        error = HTTPError(INDEX, 404, 'missing', {}, None)
        with patch('lgd_query._http.urlopen', side_effect=error) as request, patch('lgd_query._http.time.sleep'):
            with self.assertRaises(HTTPError):
                load_release(INDEX, retries=1)
            self.assertEqual(request.call_count, 2)
            self.assertTrue(all(call.args[0].full_url == INDEX for call in request.call_args_list))

    def test_metadata_download_is_size_bounded(self):
        with patch('lgd_query._http.MAX_METADATA_BYTES', 32):
            with self.assertRaisesRegex(MetadataError, 'size limit'):
                load_release(INDEX)

    def test_download_verifies_and_reuses_existing_content_without_metadata_requests(self):
        dataset = Release.from_dict(self.document).dataset('states')
        path = download(dataset, self.root)
        self.assertEqual(path.read_bytes(), b'small parquet')
        self.assertIn(dataset.parquet.sha256, path.name)
        self.assertEqual(download(dataset, self.root), path)
        self.assertEqual(self.server.requests, [dataset.parquet.url])

    def test_corrupt_downloads_leave_no_partial_file_and_preserve_existing_cache(self):
        dataset = Release.from_dict(self.document).dataset('states')
        for payload in (b'truncated', b'x'*dataset.parquet.size, b'x'*(dataset.parquet.size+1)):
            with self.subTest(payload=payload):
                self.server.files[dataset.parquet.url] = payload
                with self.assertRaises(IntegrityError):
                    download(dataset, self.root)
                self.assertEqual(list(self.root.iterdir()), [])
        self.server.files[dataset.parquet.url] = b'small parquet'
        path = download(dataset, self.root)
        path.write_bytes(b'bad cache')
        self.server.files[dataset.parquet.url] = b'bad server'
        with self.assertRaises(IntegrityError):
            download(dataset, self.root)
        self.assertEqual(path.read_bytes(), b'bad cache')
        self.assertEqual(list(self.root.iterdir()), [path])
        self.server.files[dataset.parquet.url] = b'small parquet'
        self.assertEqual(download(dataset, self.root).read_bytes(), b'small parquet')

    def test_interrupted_transfer_closes_response_and_cleans_temporary_file(self):
        dataset = Release.from_dict(self.document).dataset('states')

        class Interrupted(io.BytesIO):
            def read(self, size=-1):
                if self.tell():
                    raise ConnectionResetError('connection lost during transfer')
                return super().read(5)

        response = Interrupted(b'small parquet')
        with patch('lgd_query._http.urlopen', return_value=response):
            with self.assertRaises(ConnectionResetError):
                download(dataset, self.root)
        self.assertTrue(response.closed)
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(download(dataset, self.root).read_bytes(), b'small parquet')

    def test_simultaneous_downloads_share_only_the_verified_final_file(self):
        dataset = Release.from_dict(self.document).dataset('states')
        started = Barrier(2)

        def open_response(*args, **kwargs):
            started.wait(timeout=5)
            return io.BytesIO(b'small parquet')

        with patch('lgd_query._http.urlopen', side_effect=open_response), ThreadPoolExecutor(2) as pool:
            paths = list(pool.map(lambda _: download(dataset, self.root), range(2)))
        self.assertEqual(paths[0], paths[1])
        self.assertEqual(paths[0].read_bytes(), b'small parquet')
        self.assertEqual(list(self.root.iterdir()), [paths[0]])

    def run_cli(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(['--metadata-url', INDEX, *arguments]), 0)
        return output.getvalue()

    def test_cli_json_list_resolve_and_download_use_the_public_contract(self):
        listing = json.loads(self.run_cli('list', '--format', 'json'))
        self.assertEqual(len(listing['datasets']), 4)
        self.assertEqual(self.server.requests, [INDEX])
        resolved = json.loads(self.run_cli('resolve', 'states', '--manifest', '--format', 'json'))
        self.assertEqual(resolved['entry']['daily'], resolved['manifest']['daily'])
        result = json.loads(self.run_cli('download', 'states', '--directory', str(self.root), '--format', 'json'))
        self.assertTrue(Path(result[0]['path']).exists())

    def test_cli_errors_are_nonzero_and_do_not_print_success_json(self):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors), self.assertRaises(SystemExit) as result:
            cli.main(['--metadata-url', INDEX, 'resolve', 'districts', '--observed-on', '2026-10-23', '--format', 'json'])
        self.assertEqual(result.exception.code, 1)
        self.assertEqual(output.getvalue(), '')
        self.assertIn('2026-10-22', errors.getvalue())

    def test_missing_table_dependency_fails_before_any_requests_or_downloads(self):
        errors = io.StringIO()
        with patch.dict('sys.modules', {'rich.console': None}), redirect_stderr(errors), \
                self.assertRaises(SystemExit) as result:
            cli.main(['--metadata-url', INDEX, 'download', 'states', '--directory', str(self.root)])
        self.assertEqual(result.exception.code, 1)
        self.assertIn('lgd-query[cli]', errors.getvalue())
        self.assertEqual(self.server.requests, [])
        self.assertEqual(list(self.root.iterdir()), [])

    @unittest.skipUnless(importlib.util.find_spec('rich'), 'Rich is optional')
    def test_cli_tables_and_literal_source_text(self):
        listing = self.run_cli('list')
        self.assertIn('Dataset', listing)
        self.assertIn('states', listing)
        self.assertNotIn('"datasets":', listing)
        resolved = self.run_cli('resolve', 'states', '--manifest')
        self.assertIn('Canonical schema', resolved)
        self.assertIn('state_code', resolved)
        output = io.StringIO()
        with redirect_stdout(output):
            cli._table(['Name'], [('[bold]literal[/bold]',)])
        self.assertIn('[bold]literal[/bold]', output.getvalue())

    def test_base_api_and_json_cli_do_not_import_optional_or_repository_packages(self):
        # Test the same installed wheel as this process, not the checkout's src/.
        source = str(Path(lgd_query.__file__).resolve().parent.parent)
        script = '''
import importlib.abc, json, sys
sys.path.insert(0, sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'duckdb', 'rich', 'history', 'parquet', 'scrape', 'pyarrow', 'pyiceberg'}:
            raise ImportError('Blocked optional/repository package: ' + fullname)
sys.meta_path.insert(0, Block())
from lgd_query import Release, connect
from lgd_query.cli import main
from unittest.mock import patch
release = Release.from_dict(json.loads(sys.argv[2]))
with patch('lgd_query.cli.load_release', return_value=release):
    main(['list', '--format', 'json'])
try:
    connect([release.dataset('states')])
except ImportError as error:
    assert 'lgd-query[duckdb]' in str(error)
else:
    raise AssertionError('Optional dependency was silently required')
'''
        result = subprocess.run([sys.executable, '-I', '-c', script, source, json.dumps(self.document)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['datasets']), 4)


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class QueryTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.server = PublicFiles()
        path = self.root/'source.parquet'
        with duckdb.connect() as writer:
            writer.execute("COPY (SELECT '01' AS state_code, 'தமிழ்நாடு [name]' AS state_name) TO ? (FORMAT PARQUET)", [str(path)])
        entry = self.server.dataset('states', path.read_bytes())
        self.release = Release.from_dict(self.server.index(dict(states=entry)))
        self.enterContext(patch('lgd_query._http.urlopen', side_effect=self.server.open))

    def test_native_connection_queries_verified_cache_and_works_offline(self):
        dataset = self.release.dataset('states')
        with connect([dataset], cache_dir=self.root/'cache') as db:
            self.assertEqual(db.sql('SELECT state_name FROM states WHERE state_code=?', params=['01']).fetchall(),
                             [('தமிழ்நாடு [name]',)])
        self.assertEqual(self.server.requests, [dataset.parquet.url])
        self.server.files.clear()
        with connect([dataset], cache_dir=self.root/'cache', config={'threads': 1}) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM states').fetchone(), (1,))
        self.assertEqual(self.server.requests, [dataset.parquet.url])

    def test_remote_registration_uses_resolved_url_and_closes_on_failure(self):
        dataset = self.release.dataset('states')
        with patch('duckdb.connect') as opened:
            result = connect([dataset])
            self.assertIs(result, opened.return_value)
            result.read_parquet.assert_called_once_with(dataset.parquet.url)
            result.read_parquet.return_value.create_view.assert_called_once_with('states', replace=False)
        with patch('duckdb.connect') as opened:
            opened.return_value.read_parquet.side_effect = OSError('bad remote parquet')
            with self.assertRaises(OSError):
                connect([dataset])
            opened.return_value.close.assert_called_once()
        self.assertEqual(self.server.requests, [])

    def test_duplicate_views_rejected_before_download(self):
        dataset = self.release.dataset('states')
        with self.assertRaisesRegex(ValueError, 'unique'):
            connect([dataset, dataset], cache_dir=self.root/'cache')
        self.assertEqual(self.server.requests, [])

    def test_query_cli_json_preserves_duplicate_columns_and_bound_parameters(self):
        output = io.StringIO()
        with redirect_stdout(output):
            cli.main(['--metadata-url', INDEX, 'query',
                      'SELECT state_code AS code, state_name AS code FROM states WHERE state_code=?',
                      '--datasets', 'states', '--params', '["01"]',
                      '--cache-dir', str(self.root/'cache'), '--format', 'json'])
        result = json.loads(output.getvalue())
        self.assertEqual(result['columns'], ['code', 'code'])
        self.assertEqual(result['rows'], [['01', 'தமிழ்நாடு [name]']])
        self.assertEqual(self.server.requests.count(INDEX), 1)

    def test_json_nonfinite_values_and_nested_results_are_standard_json(self):
        import duckdb
        output = io.StringIO()
        with duckdb.connect() as connection, redirect_stdout(output):
            cursor = connection.execute("""SELECT 'NaN'::DOUBLE AS n,
                ['Infinity'::DOUBLE, '-Infinity'::DOUBLE] AS nested,
                {'value': 'NaN'::DOUBLE} AS record, 1.25 AS normal, NULL AS missing""")
            cli._query_output(cursor, 'json')

        def reject(token):
            raise ValueError(f'Nonstandard JSON token: {token}')
        result = json.loads(output.getvalue(), parse_constant=reject)
        self.assertEqual(result['rows'], [['NaN', ['Infinity', '-Infinity'],
                                          {'value': 'NaN'}, '1.25', None]])

    def test_json_maps_preserve_nonstring_keys_in_parallel_arrays(self):
        import duckdb
        output = io.StringIO()
        with duckdb.connect() as connection, redirect_stdout(output):
            cursor = connection.execute("""SELECT
                map([DATE '2026-10-24'], ['date']) AS dates,
                map([1.5], ['decimal']) AS decimals,
                map(['NaN'::DOUBLE], ['nonfinite']) AS floats,
                map([1, 2], ['one', 'two']) AS integers,
                map(['name'], ['string']) AS strings,
                {'nested': map([[1, 2]], ['list'])} AS nested""")
            cli._query_output(cursor, 'json')

        def reject(token):
            raise ValueError(f'Nonstandard JSON token: {token}')
        result = json.loads(output.getvalue(), parse_constant=reject)
        self.assertEqual(result['rows'], [[
            {'key': ['2026-10-24'], 'value': ['date']},
            {'key': ['1.5'], 'value': ['decimal']},
            {'key': ['NaN'], 'value': ['nonfinite']},
            {'key': [1, 2], 'value': ['one', 'two']},
            {'name': 'string'},
            {'nested': {'key': [[1, 2]], 'value': ['list']}},
        ]])

    @unittest.skipUnless(importlib.util.find_spec('rich'), 'Rich is optional')
    def test_query_cli_table_and_empty_result(self):
        for where in ('true', 'false'):
            with self.subTest(where=where):
                output = io.StringIO()
                with redirect_stdout(output):
                    cli.main(['--metadata-url', INDEX, 'query', 'SELECT state_code FROM states WHERE '+where,
                              '--datasets', 'states', '--cache-dir', str(self.root/'cache')])
                self.assertIn('state_code', output.getvalue())
                if where == 'true':
                    self.assertIn('01', output.getvalue())


if __name__ == '__main__':
    unittest.main()
