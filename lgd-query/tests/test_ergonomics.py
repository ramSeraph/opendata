"""Caller-facing signatures, preparation, missing values and CLI exploration."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import importlib.util
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from lgd_query import cli, queries
import test_dataset_queries as fixtures
from test_dataset_queries import SCHEMAS, create, records


class SignatureTests(unittest.TestCase):
    def test_code_keywords_and_named_filter_signatures(self):
        self.assertTrue(set(queries.DATASETS) <= set(dir(queries)))
        for dataset in queries.DATASETS:
            module = queries.get(dataset)
            if dataset == 'transactions':
                signature = inspect.signature(module.by_id)
                self.assertIn('transaction_id', signature.parameters)
                queries.prepare(dataset, 'by_id', transaction_id='001')
                continue
            signature = inspect.signature(module.by_code)
            self.assertIn('code', signature.parameters)
            self.assertNotIn('value', signature.parameters)
            scope = {'entity_type': 'Village'} if dataset in ('changes', 'constituency_coverage') else {}
            queries.prepare(dataset, 'by_code', code='001', **scope)
            signature = inspect.signature(module.list)
            if hasattr(module, 'filters'):
                self.assertTrue(set(module.filters) <= set(signature.parameters))
            self.assertIn('is_null', signature.parameters)
            self.assertIn('is_blank', signature.parameters)

    def test_generated_stubs_are_current(self):
        script = Path(__file__).resolve().parents[1]/'tools/generate_query_stubs.py'
        result = subprocess.run([sys.executable, str(script), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_preparation_requires_no_database_or_network(self):
        script = '''
import importlib.abc, sys
sys.path.insert(0, sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'duckdb','rich','history','parquet','pyarrow'}:
            raise ImportError('Unexpected dependency: '+fullname)
sys.meta_path.insert(0,Block())
from lgd_query import queries
from unittest.mock import patch
with patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected request')):
    query=queries.prepare('state_org_units','search','Office',field='entity_name',include_entity_name=True)
    assert query.required_datasets == ('state_org_units','org_unit_details')
    query=queries.prepare('org_unit_details','references',entity_type=1254,state_code='32')
    assert query.required_datasets == ('org_unit_details','state_admin_dept_units')
    assert queries.prepare('org_unit_coverage','reference_types').required_datasets == ('org_unit_coverage',)
    assert queries.org_unit_details.reference_type_map()
'''
        import lgd_query
        source = str(Path(lgd_query.__file__).resolve().parent.parent)
        result = subprocess.run([sys.executable, '-I', '-c', script, source], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class PreparedQueryTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db = duckdb.connect(config={'threads': 1})
        self.addCleanup(self.db.close)

    def test_all_generic_helpers_agree_with_prepared_queries(self):
        for dataset, schema in SCHEMAS.items():
            module = queries.get(dataset)
            spec = module._queries.spec
            row = {column: (1 if kind == 'INTEGER' else date(2026, 10, 23) if kind == 'DATE'
                            else '001' if column.endswith('_code') else 'Alpha')
                   for column, kind in schema.items()}
            row[spec.primary_code] = '001'
            row[spec.primary_name] = 'Alpha'
            create(self.db, dataset, [row, row])
            scope = {'entity_type': 'Alpha'} if spec.typed_code else {}
            calls = [('list', (), {}), ('search', ('Alph',), {'mode': 'fuzzy'}),
                     ('by_id' if dataset == 'transactions' else 'by_code', ('001',), scope)]
            calls += [('by_census_code', ('001',), {'year': year}) for year in module.census_years]
            for operation, args, options in calls:
                with self.subTest(dataset=dataset, operation=operation):
                    expected = getattr(module, operation)(self.db, *args, **options)
                    prepared = queries.prepare(dataset, operation, *args, **options)
                    actual = prepared.execute(self.db)
                    self.assertEqual(actual.columns, expected.columns)
                    self.assertEqual(actual.columns, list(prepared.columns))
                    self.assertEqual(actual.fetchall(), expected.fetchall())

    def test_prepared_enrichment_uses_one_option_set_and_keeps_fuzzy_order(self):
        base = dict(organization_code='5', state_code='32', entity_type='2', entity_code='100')
        create(self.db, 'state_org_units', [dict(base, organization_unit_code='1', organization_unit_name='Post'),
                                          dict(base, organization_unit_code='2', organization_unit_name='Posts')])
        create(self.db, 'org_unit_details', [dict(base, organization_unit_code='1', entity_name='Place'),
                                           dict(base, organization_unit_code='2', entity_name='Other')])
        for field in ('english', 'entity_name'):
            options = dict(field=field, mode='fuzzy', max_distance=8, include_entity_name=True)
            query = queries.prepare('state_org_units', 'search', 'Post', **options)
            self.assertEqual(query.required_datasets, ('state_org_units', 'org_unit_details'))
            self.assertEqual(records(query.execute(self.db)),
                             records(queries.state_org_units.search(self.db, 'Post', **options)))

    def test_missing_values_keep_null_blank_and_whitespace_distinct(self):
        create(self.db, 'constituency_coverage', [
            dict(entity_code=str(i), entity_name='Village', coverage_type=flag)
            for i, flag in enumerate((None, '', ' ', 'Fully Covered'))])
        module = queries.constituency_coverage
        self.assertEqual(len(module.list(self.db, coverage_type=None).fetchall()), 4)
        self.assertEqual(records(module.list(self.db, is_null='coverage_type'))[0]['entity_code'], '0')
        self.assertEqual(records(module.list(self.db, is_blank=['coverage_type']))[0]['entity_code'], '1')
        create(self.db, 'invalidated_census_villages', [dict(village_code='', state_code='27'),
                                                      dict(village_code='1', state_code='27')])
        self.assertEqual(records(queries.invalidated_census_villages.list(self.db, is_blank='village_code')),
                         records(queries.prepare('invalidated_census_villages', 'list',
                                                 is_blank='village_code').execute(self.db)))
        self.assertEqual(len(queries.invalidated_census_villages.list(self.db, is_blank='village_code').fetchall()), 1)
        for options in ({'is_null': 'unknown'}, {'is_blank': 'unknown'},
                        {'is_null': 'coverage_type', 'is_blank': 'coverage_type'}, {'is_null': True}):
            with self.assertRaises(ValueError):
                queries.prepare('constituency_coverage', 'list', **options)
        with self.assertRaisesRegex(ValueError, 'text columns'):
            queries.prepare('villages', 'list', is_blank='village_version')
        with self.assertRaisesRegex(ValueError, 'text columns'):
            queries.prepare('transactions', 'list', is_blank='transaction_date')

    def test_first_three_datasets_support_missing_predicates(self):
        for dataset in ('states', 'districts', 'subdistricts'):
            module = queries.get(dataset)
            fields = module.columns
            self.db.sql(f'CREATE TABLE {dataset} (' + ', '.join(
                f'{c} INTEGER' if c.endswith('_version') else f'{c} VARCHAR' for c in fields) + ')')
            row = {c: 1 if c.endswith('_version') else '001' for c in fields}
            row[fields[2] if dataset != 'districts' else 'district_name'] = 'Alpha'
            row[fields[-1]] = None
            self.db.execute(f'INSERT INTO {dataset} VALUES (' + ','.join('?' for _ in fields) + ')',
                            [row[c] for c in fields])
            for operation, args, options in (
                ('list', (), {}), ('by_code', (), {'code': '001'}),
                ('by_census_code', ('001',), {'year': 2001}), ('search', ('Alpha',), {}),
            ):
                with self.subTest(dataset=dataset, operation=operation):
                    query = queries.prepare(dataset, operation, *args, is_null=fields[-1], **options)
                    self.assertEqual(len(query.execute(self.db).fetchall()), 1)
                    self.assertEqual(queries.prepare(dataset, operation, *args,
                        is_blank=fields[-1], **options).execute(self.db).fetchall(), [])

    def test_entity_and_eci_preparations_preserve_target_columns_and_parameters(self):
        create(self.db, 'villages', [dict(village_code='100', village_name='Place', state_code='32')])
        create(self.db, 'org_unit_coverage', [dict(organization_unit_code='7',
            covered_entity_type='Village', covered_entity_code='100', coverage_details_reported='true')])
        create(self.db, 'constituency_coverage', [dict(entity_type='Village', entity_code='100', state_code='32')])
        for dataset, options in (
            ('org_unit_coverage', dict(covered_entity_type='Village', organization_unit_code='7')),
            ('constituency_coverage', dict(entity_type='Village', entity_code='100')),
        ):
            query = queries.prepare(dataset, 'entities', **options)
            result = query.execute(self.db)
            self.assertEqual(query.required_datasets, (dataset, 'villages'))
            self.assertEqual(result.columns, list(query.columns))
            self.assertEqual(records(result), records(queries.get(dataset).entities(self.db, **options)))
        create(self.db, 'constituencies_mapping_pri', [dict(state_code='6',
            assembly_constituency_code='416', assembly_constituency_eci_code='42',
            assembly_constituency_name='Name')])
        query = queries.prepare('constituencies_mapping_pri', 'eci_codes', level='assembly', eci_code='42')
        result = query.execute(self.db)
        self.assertEqual(result.columns, list(query.columns))
        self.assertEqual(result.fetchall(), queries.constituencies_mapping_pri.eci_codes(
            self.db, level='assembly', eci_code='42').fetchall())


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class ErgonomicsCLITests(unittest.TestCase):
    setUp = fixtures.ReportCLIIntegrationTests.setUp
    run_cli = fixtures.ReportCLIIntegrationTests.run_cli

    def add_transactions(self, count=25):
        import duckdb
        path = self.root/'many.parquet'
        with duckdb.connect() as db:
            create(db, 'transactions', [dict(transaction_id=f'{i:04}', description=f'Event {i:04}',
                    state_code='32', transaction_date=date(2024, 1, 1)) for i in range(count)])
            db.sql('COPY transactions TO ? (FORMAT PARQUET)', params=[str(path)])
        self.server.index({'transactions': self.server.dataset('transactions', path.read_bytes())})

    def test_preview_all_projection_and_exact_boundary(self):
        self.add_transactions()
        result = self.run_cli('transactions', 'list', '--columns', 'transaction_id', 'description')
        self.assertEqual(result['columns'], ['transaction_id', 'description'])
        self.assertEqual(len(result['rows']), 20)
        self.assertTrue(result['truncated'])
        self.assertEqual(len(self.run_cli('transactions', 'list', '--all')['rows']), 25)
        self.assertTrue(self.run_cli('transactions', 'search', 'Event', '--limit', '2')['truncated'])
        self.assertEqual(len(self.run_cli('transactions', 'search', 'Event', '--all')['rows']), 25)
        self.add_transactions(20)
        self.assertFalse(self.run_cli('transactions', 'list')['truncated'])

    def test_invalid_inputs_make_zero_requests(self):
        calls = [
            ('transactions', 'list', '--since', 'bad-date'),
            ('transactions', 'list', '--since', '2024-01-02', '--until', '2024-01-01'),
            ('transactions', 'list', '--state-code', 'no-code'),
            ('transactions', 'list', '--observed-on', '20240101'),
            ('transactions', 'list', '--limit', '0'),
            ('transactions', 'list', '--columns', 'missing'),
            ('transactions', 'list', '--is-null', 'missing'),
            ('transactions', 'search', 'x', '--max-distance', '-1'),
            ('query', 'SELECT * FROM transactions', '--datasets', 'transactions', '--params', '{'),
            ('query', 'SELECT * FROM transactions', '--datasets', 'transactions', '--params', 'null'),
        ]
        for args in calls:
            with self.subTest(args=args), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.run_cli(*args)
        self.assertEqual(self.server.requests, [])

    def test_json_provenance_preserves_dates_and_failed_update_status(self):
        entries = self.index['datasets']
        entries['states']['daily']['observed_on'] = '2026-10-22'
        entries['states']['outcome'] = {'status': 'failed', 'reason': 'New report unavailable'}
        self.server.index(entries)
        result = self.run_cli('constituencies_mapping_pri', 'search', 'Kerala',
                              '--field', 'state_name', '--provenance')
        sources = {d['dataset']: d for d in result['provenance']['sources']}
        self.assertEqual(sources['states']['observed_on'], '2026-10-22')
        self.assertEqual(sources['states']['status'], 'failed')
        self.assertEqual(sources['states']['reason'], 'New report unavailable')
        self.assertEqual(sources['constituencies_mapping_pri']['observed_on'], '2026-10-23')
        self.assertTrue(result['rows'])

    def test_cli_missing_predicates_and_table_source_context(self):
        self.assertEqual(len(self.run_cli('transactions', 'list', '--is-null', 'operation_name')['rows']), 1)
        self.assertFalse(self.run_cli('transactions', 'list', '--is-blank', 'operation_name')['rows'])
        if importlib.util.find_spec('rich'):
            output = self.run_cli('transactions', 'list', format='table')
            self.assertIn('Sources', output)
            self.assertIn('2026-10-23', output)

    def test_raw_sql_keeps_unbounded_default_and_supports_preview(self):
        self.add_transactions(25)
        args = ('query', 'SELECT transaction_id AS id, description FROM transactions ORDER BY transaction_id',
                '--datasets', 'transactions')
        result = self.run_cli(*args)
        self.assertEqual(len(result['rows']), 25)
        self.assertNotIn('truncated', result)
        result = self.run_cli(*args, '--limit', '2', '--columns', 'description', '--provenance')
        self.assertEqual(result['columns'], ['description'])
        self.assertEqual(len(result['rows']), 2)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['provenance']['sources'][0]['dataset'], 'transactions')

    def test_full_output_streams_multiple_batches(self):
        self.add_transactions(2001)
        result = self.run_cli('transactions', 'list', '--all', '--columns', 'transaction_id')
        self.assertEqual(len(result['rows']), 2001)
        self.assertEqual(result['rows'][0], ['0000'])
        self.assertEqual(result['rows'][-1], ['2000'])


if __name__ == '__main__':
    unittest.main()
