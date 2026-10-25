"""Organization exploration preserves links, unresolved evidence and source scope."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import unittest
from unittest.mock import Mock

from lgd_query import queries
from lgd_query.queries import org_unit_details, org_unit_coverage
import test_dataset_queries as fixtures
from test_dataset_queries import create, records, SCHEMAS
from test_reader import INDEX


def table(db, dataset, rows=()):
    if dataset in SCHEMAS:
        create(db, dataset, rows)
        return
    columns = queries.get(dataset).columns
    db.sql(f'CREATE TABLE {dataset} (' + ', '.join(
        f'{c} INTEGER' if c.endswith('_version') else f'{c} VARCHAR' for c in columns) + ')')
    if rows:
        db.executemany(f'INSERT INTO {dataset} VALUES (' + ','.join('?' for c in columns) + ')',
                       [[row.get(c) for c in columns] for row in rows])
        db.fetchall()


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class OrganizationExplorationTests(unittest.TestCase):
    setUp = fixtures.DatasetQueryTests.setUp

    def assert_prepared(self, dataset, operation, **options):
        q = queries.prepare(dataset, operation, **options)
        result = q.execute(self.db)
        self.assertEqual(q.columns, tuple(result.columns))
        self.assertCountEqual(result.fetchall(), getattr(queries.get(dataset), operation)(self.db, **options).fetchall())
        return records(q.execute(self.db))

    def test_custom_scope_excludes_unneeded_registers_in_both_apis(self):
        for state, target in [('32', 'state_admin_dept_units'), ('0', 'central_admin_dept_units')]:
            with self.subTest(state=state):
                table(self.db, 'org_unit_details', [dict(organization_unit_code='7', state_code=state,
                    entity_type='1254', entity_code='100001')])
                table(self.db, target, [dict(administrative_unit_code='100001',
                    administrative_unit_level_code='1254', administrative_unit_name='Location', state_code=state)])
                for operation in ('entities', 'references'):
                    q = queries.prepare('org_unit_details', operation, entity_type=1254, state_code=state)
                    self.assertEqual(q.required_datasets, ('org_unit_details', target))
                    self.assertEqual(len(self.assert_prepared('org_unit_details', operation,
                                     entity_type=1254, state_code=state)), 1)
                for method in (org_unit_details.required_entity_datasets, org_unit_details.required_reference_datasets):
                    self.assertEqual(method(1254, state_code=state), ('org_unit_details', target))
                release = Mock()
                org_unit_details.entity_sources(release, 1254, state_code=state, observed_on='2026-10-24')
                self.assertEqual([call.args[0] for call in release.dataset.call_args_list], ['org_unit_details', target])
                self.db.sql('DROP TABLE org_unit_details')
                self.db.sql(f'DROP TABLE {target}')
        self.assertEqual(org_unit_details.required_reference_datasets(1254),
                         ('org_unit_details', 'state_admin_dept_units', 'central_admin_dept_units'))

    def test_custom_mixed_scope_routes_each_office_to_its_namespace(self):
        table(self.db, 'org_unit_details', [dict(organization_unit_code=unit, state_code=state,
            entity_type='1254', entity_code='100001') for unit,state in [('1','0'),('2','32')]])
        for scope in ('state', 'central'):
            table(self.db, scope+'_admin_dept_units', [dict(administrative_unit_code='100001',
                administrative_unit_name=scope, administrative_unit_level_code='1254', state_code='32'),
                dict(administrative_unit_code='100001', administrative_unit_name='Wrong level',
                     administrative_unit_level_code='1255', state_code='32')])
        rows = self.assert_prepared('org_unit_details', 'references', entity_type=1254)
        self.assertEqual([(r['source_organization_unit_code'], r['target_name']) for r in rows],
                         [('1', 'central'), ('2', 'state')])

    def test_references_preserve_source_rows_and_all_resolution_outcomes(self):
        base = dict(organization_unit_code='1', entity_code='900', state_code='0', covered_entity_type='Village',
                    covered_entity_code='100', coverage_details_reported='true', coverage_type='F')
        rows = [base, base, dict(base, organization_unit_code='2', covered_entity_code='101'),
                dict(base, organization_unit_code='3', covered_entity_code='999'),
                dict(base, organization_unit_code='4', covered_entity_code=''),
                dict(base, organization_unit_code='5', covered_entity_code='-1'),
                dict(base, organization_unit_code='6', covered_entity_type=''),
                dict(base, organization_unit_code='7', covered_entity_type='Unknown'),
                dict(base, organization_unit_code='8', covered_entity_type='', covered_entity_code='',
                     coverage_details_reported='false', coverage_type=''),
                dict(base, organization_unit_code='9', covered_entity_code='102'),
                dict(base, organization_unit_code='10', covered_entity_type=None)]
        table(self.db, 'org_unit_coverage', rows)
        for dataset in org_unit_coverage.required_reference_datasets()[1:]:
            table(self.db, dataset, [dict(village_code='100', village_category='R', village_name='Place', state_code='32'),
                dict(village_code='100', village_category='R', village_name='Place', state_code='32'),
                dict(village_code='100', village_category='U', village_name='Place', state_code='32'),
                dict(village_code='101', village_category='R', village_name='A'),
                dict(village_code='101', village_category='R', village_name='B'),
                dict(village_code='102', village_category='R', village_name='Single')]
                if dataset == 'villages' else [])
        result = self.assert_prepared('org_unit_coverage', 'references')
        by_unit = {}
        for row in result:
            by_unit.setdefault(row['source_organization_unit_code'], []).append(row)
        self.assertEqual(len(by_unit['1']), 4)  # Two source duplicates, two distinct target variants.
        self.assertEqual(by_unit['1'][0]['target_match_count'], 2)
        self.assertEqual(by_unit['1'][0]['target_name_count'], 1)
        self.assertEqual(by_unit['2'][0]['target_name_count'], 2)
        self.assertEqual((by_unit['1'][0]['source_entity_code'], by_unit['1'][0]['target_code']), ('900', '100'))
        self.assertEqual((by_unit['1'][0]['source_state_code'], by_unit['1'][0]['target_state_code']), ('0', '32'))
        for unit,status in [('1','ambiguous'),('2','ambiguous'),('3','unmatched'),('4','missing_code'),
                            ('5','invalid_code'),('6','missing_type'),('7','unsupported_type'),
                            ('8','not_reported'),('9','matched'),('10','missing_type')]:
            self.assertEqual({r['resolution_status'] for r in by_unit[unit]}, {status})
            selected = self.assert_prepared('org_unit_coverage', 'references', resolution_status=status)
            self.assertTrue(all(r['resolution_status'] == status for r in selected))
        self.assertIsNone(by_unit['3'][0]['target_dataset'])
        self.assertEqual(by_unit['3'][0]['target_match_count'], 0)
        with self.assertRaisesRegex(ValueError, 'resolution_status'):
            queries.prepare('org_unit_coverage', 'references', resolution_status='deleted')

    def test_unknown_types_are_inspectable_but_strict_entities_reject_them(self):
        table(self.db, 'org_unit_coverage', [dict(organization_unit_code='1', covered_entity_type='SubDistrict',
            covered_entity_code='10', coverage_details_reported='true')])
        with self.assertRaisesRegex(ValueError, 'Subdistrict'):
            queries.prepare('org_unit_coverage', 'entities', covered_entity_type='SubDistrict')
        q = queries.prepare('org_unit_coverage', 'references', covered_entity_type='SubDistrict')
        self.assertEqual(q.required_datasets, ('org_unit_coverage',))
        self.assertEqual(records(q.execute(self.db))[0]['resolution_status'], 'unsupported_type')
        table(self.db, 'org_unit_details', [dict(organization_unit_code='1', entity_type='-100', entity_code='1',
                                               entity_type_name='', entity_name='Anantnag')])
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            queries.prepare('org_unit_details', 'entities', entity_type=-100)
        result = self.assert_prepared('org_unit_details', 'references', entity_type=-100)
        self.assertEqual(result[0]['source_entity_name'], 'Anantnag')
        self.assertEqual(result[0]['resolution_status'], 'unsupported_type')
        self.assertIsNone(result[0]['target_name'])

    def test_body_matches_keep_type_disagreements_and_source_links(self):
        table(self.db, 'state_org_units', [dict(organization_unit_code='1', entity_type='-5', entity_code='100')])
        for dataset,kind in [('pri_local_bodies','3'),('urban_local_bodies','5'),('traditional_local_bodies',None)]:
            table(self.db, dataset, [dict(local_body_code='100', local_body_name='Body', local_body_type_code=kind)])
        rows = self.assert_prepared('state_org_units', 'references', entity_type=-5)
        self.assertEqual({r['target_dataset']: r['reference_type_matches'] for r in rows},
                         {'pri_local_bodies':False, 'urban_local_bodies':True, 'traditional_local_bodies':None})
        self.assertTrue(all(r['resolution_status']=='ambiguous' and r['target_match_count']==3 for r in rows))

    def test_observed_types_require_only_source_and_preserve_labels(self):
        table(self.db, 'org_unit_details', [dict(organization_unit_code=unit, entity_type=kind,
            entity_type_name=label, state_code='32') for unit,kind,label in
            [('1','2','District'),('1','2','District'),('2','2','Alternative'),('3','-100',''),
             ('4','1254','Postal level'),('5',None,None)]])
        rows = self.assert_prepared('org_unit_details', 'reference_types', state_code='32')
        district = next(r for r in rows if r['reported_type_name']=='District')
        self.assertEqual((district['source_rows'],district['organization_units']), (2,1))
        custom = next(r for r in rows if r['reference_type']=='1254')
        self.assertEqual(custom['target_datasets'], ['state_admin_dept_units'])
        self.assertEqual(custom['reported_type_name'], 'Postal level')
        self.assertIsNone(custom['known_type_name'])
        self.assertTrue(custom['resolvable'])
        sentinel = next(r for r in rows if r['reference_type']=='-100')
        self.assertEqual(sentinel['reported_type_name'], '')
        self.assertIsNone(sentinel['known_type_name'])
        self.assertFalse(sentinel['resolvable'])
        self.assertEqual(queries.prepare('org_unit_details','reference_types').required_datasets, ('org_unit_details',))
        mapping = {r['reference_type']: r for r in org_unit_details.reference_type_map()}
        self.assertIsNone(mapping['-100']['known_type_name'])
        self.assertEqual(mapping['2']['target_datasets'], ('districts',))
        self.assertIn('>5', mapping)
        self.assertNotIn('>5', {r['reference_type'] for r in org_unit_coverage.reference_type_map()})

    def test_name_status_exact_and_missing_filters_precede_search_limit(self):
        for dataset,state in [('state_org_units','32'), ('central_org_units','0')]:
            base = dict(organization_code='9', state_code=state, entity_type='2', entity_code='10')
            table(self.db, dataset, [dict(base, organization_unit_code=unit, organization_unit_name='Office '+unit)
                                    for unit in ('1','2','3','4')])
            table(self.db, 'org_unit_details', [dict(base, organization_unit_code=unit, entity_name=name)
                                               for unit,name in [('1','A'),('2','B'),('2','C'),('4','')]])
            module = queries.get(dataset)
            self.assertEqual(module.required_datasets(entity_name_status='missing'), (dataset,'org_unit_details'))
            rows = self.assert_prepared(dataset, 'list', entity_name_status='missing')
            self.assertEqual([r['organization_unit_code'] for r in rows], ['3','4'])
            self.assertEqual(len(self.assert_prepared(dataset, 'list', is_null='entity_name')), 3)
            self.assertEqual(self.assert_prepared(dataset, 'list', entity_name='A')[0]['organization_unit_code'], '1')
            ambiguous = self.assert_prepared(dataset, 'by_code', code='2', entity_name_status='ambiguous')
            self.assertEqual(ambiguous[0]['entity_names'], ['B','C'])
            for mode in ('contains', 'fuzzy'):
                q = queries.prepare(dataset, 'search', 'Office', mode=mode, max_distance=3,
                                    entity_name_status='missing', limit=1)
                result = q.execute(self.db)
                self.assertEqual(q.columns, tuple(result.columns))
                self.assertEqual(records(result)[0]['organization_unit_code'], '3')
            self.assertEqual(module.search(self.db, 'B', field='entity_name', entity_name_status='missing').fetchall(), [])
            with self.assertRaisesRegex(ValueError, 'entity_name_status'):
                queries.prepare(dataset, 'list', entity_name_status='verified')
            self.db.sql('DROP TABLE org_unit_details')


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class OrganizationExplorationCLITests(unittest.TestCase):
    setUp = fixtures.ReportCLIIntegrationTests.setUp
    run_cli = fixtures.ReportCLIIntegrationTests.run_cli

    def inputs(self):
        import duckdb
        entries = {}
        with duckdb.connect() as db:
            base = dict(organization_unit_code='1', organization_unit_name='Office', organization_code='9',
                        state_code='32', entity_type='1254', entity_code='10')
            data = {
                'state_org_units':[base,dict(base,organization_unit_code='2')],
                'org_unit_details':[dict(base,entity_name='Place',entity_type_name='Postal level')],
                'state_admin_dept_units':[dict(administrative_unit_code='10',administrative_unit_level_code='1254',
                                              administrative_unit_name='Target',state_code='32')],
                'org_unit_coverage':[dict(organization_unit_code='1',covered_entity_type='New type',
                                          covered_entity_code='10',coverage_details_reported='true')],
            }
            for dataset,rows in data.items():
                table(db,dataset,rows)
                path = self.root/(dataset+'.parquet')
                db.sql(f'COPY {dataset} TO ? (FORMAT PARQUET)', params=[str(path)])
                entries[dataset] = self.server.dataset(dataset,path.read_bytes())
        return entries

    def test_cli_scope_references_projection_types_and_provenance(self):
        entries = self.inputs()
        entries['central_admin_dept_units'] = {'outcome':{'status':'unavailable','reason':'No source'}}
        self.server.index(entries)
        result = self.run_cli('org_unit_details','references','--entity-type','1254','--state-code','32',
            '--columns','source_organization_unit_code','target_name','resolution_status','--provenance')
        self.assertEqual(result['rows'], [['1','Target','matched']])
        self.assertEqual([d['dataset'] for d in result['provenance']['sources']],
                         ['org_unit_details','state_admin_dept_units'])
        self.run_cli('org_unit_details','entities','--entity-type','1254','--state-code','32')
        self.server.requests.clear()
        result = self.run_cli('org_unit_details','types')
        row = dict(zip(result['columns'],result['rows'][0]))
        self.assertEqual(row['reported_type_name'],'Postal level')
        self.assertEqual(self.server.requests, [INDEX])  # Cached source, no target requests.
        unknown = self.run_cli('org_unit_coverage','references','--covered-entity-type','New type')
        self.assertEqual(unknown['rows'][0][unknown['columns'].index('resolution_status')], 'unsupported_type')
        self.assertIn('Target',self.run_cli('org_unit_details','references','--entity-type','1254',
                                          '--state-code','32',format='table'))

    def test_cli_enriched_filters_and_preflight(self):
        self.server.index(self.inputs())
        result = self.run_cli('state_org_units','search','Office','--entity-name-status','missing',
                             '--limit','1','--columns','organization_unit_code','entity_name_status')
        self.assertEqual(result['rows'], [['2','missing']])
        result = self.run_cli('state_org_units','list','--is-null','entity_name')
        self.assertEqual(len(result['rows']),1)
        self.server.requests.clear()
        for args in [('org_unit_coverage','entities','--covered-entity-type','SubDistrict'),
                     ('org_unit_details','references','--resolution-status','deleted'),
                     ('state_org_units','list','--entity-name-status','verified'),
                     ('org_unit_details','references','--entity-type','1254','--state-code','bad')]:
            with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                self.run_cli(*args)
        self.assertEqual(self.server.requests, [])

    def test_missing_required_register_and_date_guard_still_fail(self):
        entries = self.inputs()
        entries['state_admin_dept_units']['daily']['observed_on'] = '2026-10-22'
        self.server.index(entries)
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('org_unit_details','references','--entity-type','1254','--state-code','32',
                         '--observed-on','2026-10-23')
        self.assertEqual(self.server.requests, [INDEX])
        self.server.requests.clear()
        entries['state_admin_dept_units'] = {'outcome':{'status':'unavailable','reason':'No source'}}
        self.server.index(entries)
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('org_unit_details','references','--entity-type','1254','--state-code','32')
        self.assertEqual(self.server.requests,[INDEX])

    def test_help_distinguishes_scope_location_and_coverage(self):
        from lgd_query import cli
        for command, expected in [('references','source_'), ('types','namespace is known'),
                                  ('entities','source offices/claims')]:
            out = io.StringIO()
            with redirect_stdout(out),self.assertRaises(SystemExit) as result:
                cli.main(['org_unit_coverage',command,'--help'])
            self.assertEqual(result.exception.code,0)
            help_text = ' '.join(out.getvalue().split())
            self.assertIn(expected,help_text)
            self.assertIn('not zero coverage',help_text)
            self.assertIn('not a universal LGD',help_text)
        self.assertEqual(self.server.requests,[])
