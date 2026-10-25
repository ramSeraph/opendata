"""Organization entity namespaces, report scopes and CLI register lookups."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from lgd_query import Release, cli, queries
from lgd_query.queries import state_org_units, central_org_units, org_unit_details, org_unit_coverage
from test_dataset_queries import create, records
from test_reader import INDEX, BASE, PublicFiles


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class OrganizationEntityTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db = duckdb.connect()
        self.addCleanup(self.db.close)

    def test_location_type_selects_namespace_and_not_organization_state(self):
        self.db.sql("""CREATE TABLE districts AS SELECT * FROM (VALUES
            ('001', 'Register district', '17'), ('1', 'Different code', '32'))
            AS t(district_code, district_name, state_code)""")
        for module in (state_org_units, central_org_units, org_unit_details):
            with self.subTest(dataset=module.__name__):
                dataset = module._queries.spec.dataset
                row = dict(organization_unit_code='7', organization_code='9',
                           state_code='32', entity_type='2', entity_code='001')
                create(self.db, dataset, [row, row, dict(row, organization_unit_code='8',
                    entity_type='3'), dict(row, entity_code='999', organization_unit_code='9')])
                result = records(module.entities(self.db, entity_type=2, organization_unit_code='7'))
                self.assertEqual(len(result), 1)
                self.assertEqual((result[0]['entity_name'], result[0]['entity_dataset'],
                                  result[0]['state_code'], result[0]['entity_code']),
                                 ('Register district', 'districts', '17', '001'))
                self.assertTrue(result[0]['reference_type_matches'])
                self.assertEqual(module.entities(self.db, entity_type=2, organization_unit_code='8').fetchall(), [])
                self.assertEqual(module.entities(self.db, entity_type=2, entity_code='999').fetchall(), [])
                self.assertEqual(len(module.by_code(self.db, '9').fetchall()), 1)

    def test_custom_levels_use_type_code_and_separate_admin_unit_namespaces(self):
        row = dict(organization_unit_code='7', organization_code='9',
                   state_code='32', entity_type='1254', entity_code='100001')
        for module in (state_org_units, central_org_units, org_unit_details):
            create(self.db, module._queries.spec.dataset,
                   [row, dict(row, organization_unit_code='8', state_code='0')])
        admin = dict(administrative_unit_code='100001', administrative_unit_level_code='1254', state_code='32')
        create(self.db, 'state_admin_dept_units', [dict(admin, administrative_unit_name='State unit'),
            dict(admin, administrative_unit_name='Wrong level', administrative_unit_level_code='1253'),
            dict(admin, administrative_unit_name='Wrong state', state_code='17')])
        create(self.db, 'central_admin_dept_units', [dict(admin, administrative_unit_name='Central unit'),
            dict(admin, administrative_unit_name='Wrong central level', administrative_unit_level_code='1253')])
        self.assertEqual([r['entity_name'] for r in records(state_org_units.entities(self.db, entity_type=1254))],
                         ['State unit'])
        self.assertEqual([r['entity_name'] for r in records(central_org_units.entities(self.db, entity_type=1254))],
                         ['Central unit'])
        for unit, expected in [('7', 'State unit'), ('8', 'Central unit')]:
            result = records(org_unit_details.entities(self.db, entity_type='1254', organization_unit_code=unit))
            self.assertEqual([r['entity_name'] for r in result], [expected])

    def test_body_codes_resolve_across_registers_and_flag_type_disagreements(self):
        create(self.db, 'state_org_units', [dict(organization_unit_code='7', state_code='32',
                                               entity_type='-5', entity_code='10')])
        for dataset, kind in [('pri_local_bodies', '3'), ('urban_local_bodies', '5'),
                              ('traditional_local_bodies', None)]:
            create(self.db, dataset, [dict(local_body_code='10', local_body_name=dataset,
                                          local_body_type_code=kind, state_code='32')])
        result = records(state_org_units.entities(self.db, entity_type=-5))
        self.assertEqual({r['entity_dataset']: r['reference_type_matches'] for r in result},
                         {'pri_local_bodies': False, 'urban_local_bodies': True,
                          'traditional_local_bodies': None})
        self.assertTrue(all(r['entity_type'] == '-5' for r in result))
        self.assertIn('intermediate_panchayat_code', result[0])

    def test_coverage_resolves_target_and_retains_register_variants(self):
        row = dict(organization_unit_code='7', state_code='0', entity_code='999',
                   covered_entity_type='Village', covered_entity_code='100', coverage_details_reported='true',
                   coverage_type='F')
        create(self.db, 'org_unit_coverage', [row, row, dict(row, coverage_type='P'),
            dict(row, covered_entity_type='District'), dict(row, covered_entity_code='101',
                                                           coverage_details_reported='false')])
        village = dict(village_code='100', village_name='Reference village', village_category='R', state_code='32')
        create(self.db, 'villages', [village, village, dict(village, village_category='U'),
                                    dict(village, village_code='999'), dict(village, village_code='101')])
        result = records(org_unit_coverage.entities(self.db, covered_entity_type='Village', organization_unit_code=7))
        self.assertEqual([r['village_category'] for r in result], ['R', 'R', 'U'])
        self.assertTrue(all(r['entity_code'] == '100' and r['state_code'] == '32' for r in result))
        self.assertEqual(len(org_unit_coverage.entities(self.db, covered_entity_type='Village', coverage_type='P').fetchall()), 3)

    def test_coverage_body_types_are_not_district_or_village_codes(self):
        create(self.db, 'org_unit_coverage', [dict(organization_unit_code='7', state_code='0',
            covered_entity_type='Village Panchayat', covered_entity_code='100', coverage_details_reported='true')])
        for dataset in ('pri_local_bodies', 'urban_local_bodies', 'traditional_local_bodies'):
            create(self.db, dataset, [dict(local_body_code='100', local_body_name='Body', local_body_type_code='3')]
                   if dataset == 'pri_local_bodies' else [])
        result = records(org_unit_coverage.entities(self.db, covered_entity_type='Village Panchayat'))
        self.assertEqual([r['entity_dataset'] for r in result], ['pri_local_bodies'])
        self.assertTrue(result[0]['reference_type_matches'])

    def test_unknown_types_and_sentinels_do_not_resolve_by_accidental_code_match(self):
        create(self.db, 'central_org_units', [dict(organization_unit_code=str(i), entity_type=kind,
            entity_code='1') for i, kind in enumerate(['0', '-100', '-99'])])
        for kind in ['0', '-100', '-99']:
            self.assertEqual(central_org_units.required_reference_datasets(kind), ('central_org_units',))
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                central_org_units.entities(self.db, entity_type=kind)
            self.assertEqual(records(central_org_units.references(self.db, entity_type=kind))[0]['resolution_status'],
                             'unsupported_type')
        create(self.db, 'org_unit_coverage', [dict(covered_entity_type=kind, covered_entity_code='1',
            coverage_details_reported='true') for kind in ['', 'Unrecognized', "Village'; DROP TABLE states;--"]])
        for kind in ['', 'Unrecognized', "Village'; DROP TABLE states;--"]:
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                org_unit_coverage.entities(self.db, covered_entity_type=kind)
            result = records(org_unit_coverage.references(self.db, covered_entity_type=kind))
            self.assertEqual(result[0]['resolution_status'], 'missing_type' if kind == '' else 'unsupported_type')
        self.db.sql('CREATE TABLE states(state_code VARCHAR,state_name VARCHAR)')
        self.db.executemany('INSERT INTO states VALUES (?, ?)', [('0', 'zero'), ('00', 'zeros'), ('-1', 'negative')])
        self.db.fetchall()
        create(self.db, 'state_org_units', [dict(entity_type='1', entity_code=code) for code in ['0', '00', '-1', '']])
        self.assertEqual(state_org_units.entities(self.db, entity_type=1).fetchall(), [])

    def test_validation_and_minimal_dependencies(self):
        db = Mock()
        for module in (state_org_units, central_org_units, org_unit_details):
            for kind in [None, True, 2.0, [], 'District', "2'; --"]:
                with self.assertRaises(ValueError): module.entities(db, entity_type=kind)
            with self.assertRaises(ValueError): module.entities(db, organization_unit_code='7')
            self.assertEqual(module.required_entity_datasets(2), (module._queries.spec.dataset, 'districts'))
        with self.assertRaisesRegex(ValueError, 'covered_entity_type is required'):
            org_unit_coverage.entities(db, entity_code='1')
        with self.assertRaises(ValueError): org_unit_coverage.entities(db, covered_entity_type=2)
        with self.assertRaises(ValueError): state_org_units.entities(db, entity_type=2, imaginary_code='7')
        db.sql.assert_not_called()
        self.assertEqual(state_org_units.required_entity_datasets(1254), ('state_org_units', 'state_admin_dept_units'))
        self.assertEqual(central_org_units.required_entity_datasets(1254), ('central_org_units', 'central_admin_dept_units'))
        self.assertEqual(org_unit_details.required_entity_datasets(1254),
                         ('org_unit_details', 'state_admin_dept_units', 'central_admin_dept_units'))
        release = Mock()
        org_unit_coverage.entity_sources(release, 'Village', observed_on='2026-10-23')
        self.assertEqual([c.args[0] for c in release.dataset.call_args_list], ['org_unit_coverage', 'villages'])
        self.assertTrue(all(c.kwargs == {'observed_on': '2026-10-23'} for c in release.dataset.call_args_list))


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class OrganizationEntityCLITests(unittest.TestCase):
    def setUp(self):
        import duckdb
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.server = PublicFiles()
        entries = {}
        with duckdb.connect() as db:
            db.sql("CREATE TABLE districts AS SELECT '10' district_code, 'Reference' district_name, '32' state_code")
            row = dict(organization_unit_code='7', organization_code='9', state_code='32', entity_type='2', entity_code='10')
            for name in ('state_org_units', 'central_org_units', 'org_unit_details'):
                create(db, name, [row])
            create(db, 'org_unit_coverage', [dict(row, covered_entity_type='District', covered_entity_code='10',
                                                coverage_details_reported='true')])
            for name in ('state_org_units', 'central_org_units', 'org_unit_details', 'org_unit_coverage', 'districts'):
                path = self.root / (name + '.parquet')
                db.sql(f'COPY {name} TO ? (FORMAT PARQUET)', params=[str(path)])
                entries[name] = self.server.dataset(name, path.read_bytes())
        self.index = self.server.index(entries)
        self.enterContext(patch('lgd_query._http.urlopen', side_effect=self.server.open))

    def run_cli(self, dataset, *args, format='json'):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(['--metadata-url', INDEX, dataset, 'entities', *args,
                '--cache-dir', str(self.root/'cache'), '--format', format]), 0)
        return json.loads(output.getvalue()) if format == 'json' else output.getvalue()

    def test_all_four_reports_load_registers_support_json_and_tables(self):
        for name in ('state_org_units', 'central_org_units', 'org_unit_details', 'org_unit_coverage'):
            flag, kind = ('--covered-entity-type', 'District') if name == 'org_unit_coverage' else ('--entity-type', '2')
            result = self.run_cli(name, flag, kind, '--organization-unit-code', '7')
            self.assertEqual(result['rows'][0][:5], ['districts', kind, '10', 'Reference', True])
        self.assertEqual(self.server.requests.count(BASE+'districts.parquet'), 1)
        self.assertIn('Reference', self.run_cli('state_org_units', '--entity-type', '2', format='table'))
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_cli('org_unit_coverage', '--entity-type', 'District')

    def test_missing_register_and_date_guard_fail_before_downloading(self):
        self.index['datasets']['districts']['daily']['observed_on'] = '2026-10-22'
        self.server.index(self.index['datasets'])
        with self.assertRaises(ValueError):
            state_org_units.entity_sources(Release.from_dict(self.index), 2, observed_on='2026-10-23')
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_cli('state_org_units', '--entity-type', '2', '--observed-on', '2026-10-23')
        self.assertEqual(self.server.requests, [INDEX])
        self.server.requests.clear()
        self.index['datasets']['districts'] = {'outcome': {'status': 'unavailable', 'reason': 'No source'}}
        self.server.index(self.index['datasets'])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_cli('org_unit_coverage', '--covered-entity-type', 'District')
        self.assertEqual(self.server.requests, [INDEX])


if __name__ == '__main__':
    unittest.main()
