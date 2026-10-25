"""Optional location labels preserve unit rows and reference ambiguity."""

from contextlib import redirect_stderr
import importlib.util
import io
import unittest

from lgd_query import Release, queries
import test_dataset_queries as fixtures
from test_reader import BASE, INDEX

create, records = fixtures.create, fixtures.records


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class OrganizationUnitQueryTests(unittest.TestCase):
    setUp = fixtures.DatasetQueryTests.setUp

    def test_optional_output_keeps_missing_rows_duplicates_and_all_labels(self):
        for dataset,state in (('state_org_units','32'),('central_org_units','0')):
            with self.subTest(dataset=dataset):
                module=queries.get(dataset)
                row=dict(organization_unit_code='7',organization_unit_name='Alpha',
                         organization_code='5',state_code=state,entity_type='-5',entity_code='10')
                create(self.db,dataset,[row,row,dict(row,organization_unit_code='8',organization_unit_name='Beta'),
                                       dict(row,organization_unit_code='9',organization_unit_name='Alph')])
                self.assertNotIn('entity_name',module.list(self.db).columns)
                base=dict(organization_unit_code='7',organization_code='5',state_code=state,
                          entity_type='-5',entity_code='10')
                create(self.db,'org_unit_details',[
                    dict(base,entity_name='Place'),dict(base,entity_name='Place'),
                    dict(base,organization_unit_code='9',entity_name='B'),
                    dict(base,organization_unit_code='9',entity_name='A'),
                    dict(base,entity_name='Wrong type',entity_type='-6'),
                    dict(base,entity_name='Wrong entity',entity_code='11'),
                    dict(base,entity_name='Wrong unit',organization_unit_code='70'),
                    dict(base,entity_name='Wrong organization',organization_code='50'),
                    dict(base,entity_name='Wrong scope',state_code='99'),
                    dict(base,entity_name='  '),dict(base,entity_name=None)])
                result=records(module.list(self.db,include_entity_name=True))
                self.assertEqual(len(result),4)
                self.assertEqual([(r['entity_name'],r['entity_names']) for r in result if r['organization_unit_code']=='7'],
                                 [('Place',['Place']),('Place',['Place'])])
                missing=next(r for r in result if r['organization_unit_code']=='8')
                self.assertEqual((missing['entity_name'],missing['entity_names']),(None,[]))
                ambiguous=next(r for r in result if r['organization_unit_code']=='9')
                self.assertEqual((ambiguous['entity_name'],ambiguous['entity_names']),(None,['A','B']))
                by_code=records(module.by_code(self.db,'7',organization_code='5',include_entity_name=True))
                self.assertEqual([r['entity_name'] for r in by_code],['Place','Place'])
                fuzzy=records(module.search(self.db,'Alph',mode='fuzzy',max_distance=1,limit=1,include_entity_name=True))
                self.assertEqual((fuzzy[0]['organization_unit_code'],fuzzy[0]['distance'],fuzzy[0]['entity_names']),('9',0,['A','B']))
                names=records(module.search(self.db,'Place',field='entity_name',include_entity_name=True))
                self.assertEqual(len(names),2)
                self.assertEqual(names[0]['lookup_names'],names[0]['entity_names'])
                self.assertEqual(module.required_datasets(),(dataset,))
                self.assertEqual(module.required_datasets(include_entity_name=True),(dataset,'org_unit_details'))
                self.assertEqual(queries.required_datasets(dataset,field='entity_name',include_entity_name=True),
                                 (dataset,'org_unit_details'))
                self.assertEqual(queries.required_datasets(dataset,field='organization_level_name',include_entity_name=True),
                                 (dataset,'org_unit_coverage','org_unit_details'))
                with self.assertRaisesRegex(ValueError,'boolean'):
                    module.list(self.db,include_entity_name='yes')
                self.db.sql('DROP TABLE org_unit_details')
        with self.assertRaisesRegex(ValueError,'supported'):
            queries.required_datasets('villages',include_entity_name=True)


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class OrganizationUnitCLITests(unittest.TestCase):
    setUp = fixtures.ReportCLIIntegrationTests.setUp
    run_cli = fixtures.ReportCLIIntegrationTests.run_cli

    def prepare(self):
        import duckdb
        with duckdb.connect() as db:
            row=dict(organization_unit_code='7',organization_unit_name='Office',
                     organization_code='5',state_code='32',entity_type='-5',entity_code='10')
            create(db,'state_org_units',[row])
            create(db,'org_unit_details',[dict(row,entity_name='Place')])
            entries={}
            for name in ('state_org_units','org_unit_details'):
                path=self.root/f'{name}.parquet'
                db.sql(f'COPY {name} TO ? (FORMAT PARQUET)',params=[str(path)])
                entries[name]=self.server.dataset(name,path.read_bytes())
        return entries

    def test_cli_flag_loads_details_only_when_requested_and_reuses_cache(self):
        self.server.index(self.prepare())
        plain=self.run_cli('state_org_units','list')
        self.assertNotIn('entity_name',plain['columns'])
        self.assertNotIn(BASE+'org_unit_details.parquet',self.server.requests)
        joined=self.run_cli('state_org_units','code','7','--include-entity-name')
        self.assertEqual(dict(zip(joined['columns'],joined['rows'][0]))['entity_name'],'Place')
        self.assertEqual(self.server.requests.count(BASE+'org_unit_details.parquet'),1)
        self.run_cli('state_org_units','search','Office','--include-entity-name')
        self.assertEqual(self.server.requests.count(BASE+'org_unit_details.parquet'),1)
        self.assertIn('Place',self.run_cli('state_org_units','list','--include-entity-name',format='table'))

    def test_date_guard_and_missing_dependency_fail_before_downloads(self):
        entries=self.prepare()
        entries['org_unit_details']['daily']['observed_on']='2026-10-22'
        index=self.server.index(entries)
        inputs=queries.sources(Release.from_dict(index),'state_org_units',include_entity_name=True)
        self.assertEqual([d.name for d in inputs],['state_org_units','org_unit_details'])
        with self.assertRaises(ValueError):
            queries.sources(Release.from_dict(index),'state_org_units',include_entity_name=True,observed_on='2026-10-23')
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('state_org_units','list','--include-entity-name','--observed-on','2026-10-23')
        self.assertEqual(self.server.requests,[INDEX])
        self.server.requests.clear()
        entries['org_unit_details']={'outcome':{'status':'unavailable','reason':'No source'}}
        self.server.index(entries)
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('state_org_units','list','--include-entity-name')
        self.assertEqual(self.server.requests,[INDEX])


if __name__=='__main__':
    unittest.main()
