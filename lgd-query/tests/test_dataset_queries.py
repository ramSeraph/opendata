"""Report contracts, ambiguous relationships, name dependencies and events."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from lgd_query import Release, connect
from lgd_query import cli, queries
from test_reader import INDEX, PublicFiles


SCHEMAS = json.loads((Path(__file__).parent/'fixtures/query_schemas.json').read_text())


def create(db, dataset, rows):
    schema = SCHEMAS[dataset]
    db.sql(f'CREATE TABLE {dataset} ('+', '.join(f'{name} {kind}' for name, kind in schema.items())+')')
    if rows:
        db.executemany(f'INSERT INTO {dataset} VALUES ('+', '.join('?' for _ in schema)+')',
                       [[row.get(column) for column in schema] for row in rows])
        db.fetchall()


def records(relation):
    columns = relation.columns
    return [dict(zip(columns, row)) for row in relation.fetchall()]


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class DatasetQueryTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db = duckdb.connect()
        self.addCleanup(self.db.close)

    def test_every_report_matches_independent_schema_and_retains_all_rows(self):
        self.assertEqual(set(queries.DATASETS)-{'states','districts','subdistricts'}, set(SCHEMAS))
        for dataset, schema in SCHEMAS.items():
            with self.subTest(dataset=dataset):
                module = queries.get(dataset)
                spec = module._queries.spec
                self.assertEqual(spec.columns, tuple(schema))
                row = {column: (3 if kind == 'INTEGER' else date(2026,10,23) if kind == 'DATE'
                                else '001' if column.endswith('_code') else 'Alpha')
                       for column, kind in schema.items()}
                row[spec.primary_code] = '001'
                row[spec.primary_name] = 'Alpha'
                other = dict(row, **{spec.primary_code: '002', spec.primary_name: 'Elsewhere'})
                create(self.db, dataset, [row, row, other])
                listed = module.list(self.db)
                self.assertEqual(listed.columns, list(schema))
                self.assertEqual(len(listed.fetchall()), 3)
                lookup = module.by_id if dataset == 'transactions' else module.by_code
                scope = {'entity_type': row['entity_type']} if spec.typed_code else {}
                self.assertEqual(len(lookup(self.db, '001', **scope).fetchall()), 2)
                self.assertEqual(lookup(self.db, '999', **scope).fetchall(), [])
                for mode in ('exact', 'prefix', 'contains', 'fuzzy'):
                    result = module.search(self.db, 'alpha', mode=mode).fetchall()
                    self.assertEqual(len(result), 2, (dataset, mode))
                    if mode == 'fuzzy':
                        self.assertEqual([r[-1] for r in result], [0,0])
                for year in module.census_years:
                    self.assertEqual(len(module.by_census_code(self.db, '001', year=year).fetchall()), 3)
                    self.assertEqual(module.by_census_code(self.db, 1, year=year).fetchall(), [])
                self.assertEqual(module.required_datasets(), (dataset,))

    def test_all_reported_and_lookup_name_fields_bind(self):
        for dataset, schema in SCHEMAS.items():
            create(self.db, dataset, [])
        self.db.sql('CREATE TABLE states (state_code VARCHAR, state_name VARCHAR)')
        for dataset in SCHEMAS:
            module = queries.get(dataset)
            for field in module.name_fields:
                with self.subTest(dataset=dataset, field=field):
                    for mode in ('exact', 'prefix', 'contains', 'fuzzy'):
                        self.assertEqual(module.search(self.db, 'x', field=field, mode=mode).fetchall(), [])

    def test_village_categories_and_local_names_preserve_evidence(self):
        base = dict(village_code='100', village_name='Kollam', village_name_local='Cafe\u0301',
                    village_version=2, state_code='32', district_code='559', subdistrict_code='5688')
        create(self.db, 'villages', [dict(base,village_category='R'),dict(base,village_category='U'),
                                   dict(base,village_code='101',district_code='560',village_name='Kolam')])
        module = queries.get('villages')
        self.assertEqual(len(module.by_code(self.db, 100).fetchall()), 2)
        self.assertEqual(len(module.list(self.db, village_category='R').fetchall()), 1)
        self.assertEqual(len(module.search(self.db, 'CAFÉ', field='local', mode='exact').fetchall()), 3)
        result = records(module.search(self.db, 'kolam', mode='fuzzy', district_code='559',
                                        subdistrict_code='5688', limit=1))
        self.assertEqual((result[0]['village_code'],result[0]['distance']), ('100',1))
        self.assertEqual(module.list(self.db,state_code='33',district_code='559').fetchall(), [])

    def test_blocks_and_ward_variants_are_associations_not_unique_entities(self):
        create(self.db,'blocks',[dict(block_code='5',block_name='Block',district_code='1'),
                                 dict(block_code='5',block_name='Block',district_code='2')])
        blocks=queries.get('blocks')
        self.assertEqual(len(blocks.by_code(self.db,5).fetchall()),2)
        self.assertEqual(records(blocks.list(self.db,district_code=2))[0]['district_code'],'2')
        create(self.db,'pri_local_body_wards',[
            dict(ward_code='7',ward_name='East',ward_number='01',local_body_code='5',local_body_name='Body'),
            dict(ward_code='8',ward_name='West',ward_number='01',local_body_code='5',local_body_name='Body')])
        wards=queries.get('pri_local_body_wards')
        self.assertEqual(len(wards.by_code(self.db,7).fetchall()),1)
        self.assertEqual(len(wards.list(self.db,ward_number='01').fetchall()),2)
        self.assertEqual(wards.list(self.db,ward_number='1').fetchall(),[])

    def test_literal_names_parent_fields_and_postal_many_to_many(self):
        create(self.db,'pincode_villages',[
            dict(village_code='1',village_name="O'Brien_100%",pincode='012345',district_name='Supplied'),
            dict(village_code='1',village_name="O'Brien_100%",pincode='654321',district_name='Supplied')])
        module=queries.get('pincode_villages')
        for name in ("O'Brien",'_', '%'):
            self.assertEqual(len(module.search(self.db,name).fetchall()),2)
        self.assertEqual(module.search(self.db,"' OR TRUE --").fetchall(),[])
        self.assertEqual(len(module.search(self.db,'supplied',field='district_name').fetchall()),2)
        self.assertEqual(len(module.list(self.db,pincode='012345').fetchall()),1)

    def test_external_state_name_lookup_has_no_row_fanout_or_name_join(self):
        create(self.db,'constituencies_mapping_pri',[
            dict(village_code='1',village_name='A',state_code='32'),
            dict(village_code='1',village_name='A',state_code='32'),
            dict(village_code='2',village_name='Kerala',state_code='99')])
        self.db.sql("CREATE TABLE states AS SELECT * FROM (VALUES ('32','Kerala'),"
                    "('32','Kerala alternate'),('32','Kerala')) t(state_code,state_name)")
        module=queries.get('constituencies_mapping_pri')
        self.assertEqual(module.required_datasets(field='state_name'),('constituencies_mapping_pri','states'))
        self.assertEqual(len(module.list(self.db).fetchall()),3)
        result=records(module.search(self.db,'kerala',field='state_name',mode='exact'))
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]['lookup_names'],['Kerala','Kerala alternate'])
        self.assertEqual(result[0]['village_name'],'A')
        result=records(module.search(self.db,'kerla',field='state_name',mode='fuzzy',limit=1))
        self.assertEqual((result[0]['village_code'],result[0]['distance']),('1',1))
        self.assertEqual(module.search(self.db,'Kerala',field='state_name',state_code=99).fetchall(),[])

    def test_parent_body_and_organization_level_lookups_are_scoped(self):
        create(self.db,'pri_local_bodies',[
            dict(local_body_code='1',local_body_name='Parent',state_code='32'),
            dict(local_body_code='2',local_body_name='Child',parent_local_body_code='1',state_code='32'),
            dict(local_body_code='3',local_body_name='Other',parent_local_body_code='1',state_code='33')])
        module=queries.get('pri_local_bodies')
        result=records(module.search(self.db,'Parent',field='parent_local_body_name'))
        self.assertEqual([r['local_body_code'] for r in result],['2'])
        create(self.db,'state_org_units',[
            dict(organization_unit_code='7',organization_unit_name='Unit',organization_code='5',
                 organization_level_code='1',state_code='32'),
            dict(organization_unit_code='8',organization_unit_name='Descendant',organization_code='5',
                 organization_level_code='2',state_code='32')])
        create(self.db,'org_unit_coverage',[
            dict(organization_unit_code='7',organization_code='5',report_organization_level_code='1',
                 report_organization_level_name='District',state_code='32'),
            dict(organization_unit_code='8',organization_code='5',report_organization_level_code='1',
                 report_organization_level_name='District',state_code='32'),
            dict(organization_unit_code='7',organization_code='6',report_organization_level_code='1',
                 report_organization_level_name='Wrong scope',state_code='32')])
        module=queries.get('state_org_units')
        result=records(module.search(self.db,'District',field='organization_level_name'))
        self.assertEqual([r['organization_unit_code'] for r in result],['7'])
        self.assertEqual(module.search(self.db,'Wrong',field='organization_level_name').fetchall(),[])

    def test_organization_identifiers_and_unknown_coverage_types(self):
        create(self.db,'org_unit_details',[dict(organization_unit_code='1',organization_unit_name='Office',
              organization_unit_specific_code='AB 001',entity_type='-5',entity_code='-1')])
        module=queries.get('org_unit_details')
        self.assertEqual(len(module.list(self.db,organization_unit_specific_code='AB 001',
                                        entity_type=-5,entity_code=-1).fetchall()),1)
        create(self.db,'org_unit_coverage',[
            dict(organization_unit_code='1',organization_unit_name='Office',covered_entity_code='5',
                 entity_code='-1', covered_entity_type='',covered_entity_name='',coverage_details_reported='true'),
            dict(organization_unit_code='1',organization_unit_name='Office',covered_entity_code='',
                 covered_entity_type='',covered_entity_name='',coverage_details_reported='false')])
        module=queries.get('org_unit_coverage')
        self.assertEqual(len(module.by_code(self.db,1).fetchall()),2)
        self.assertEqual(module.search(self.db,'Office',field='covered_entity_name').fetchall(),[])
        self.assertEqual(len(module.list(self.db,coverage_details_reported='false').fetchall()),1)
        self.assertEqual(len(module.list(self.db,entity_code=-1).fetchall()),1)

    def test_traditional_parents_resolve_both_registers_without_multiplying_rows(self):
        village = dict(local_body_level='Village', state_code='16')
        pri_child = dict(village, local_body_code='253927', local_body_name='Deoracherra',
                         district_panchayat_code='589', intermediate_panchayat_code='2886')
        create(self.db, 'traditional_local_bodies', [
            dict(state_code='16', local_body_code='6910', local_body_name='Tribal Council', local_body_level='District'),
            dict(state_code='16', local_body_code='6918', local_body_name='Ambassa Bac', local_body_level='Intermediate'),
            dict(village, local_body_code='253794', local_body_name='Bagmara',
                 district_panchayat_code='6910', intermediate_panchayat_code='6918'),
            pri_child, pri_child,
            dict(state_code='16', local_body_code='589', local_body_name='Unakoti alternate'),
            dict(state_code='16', local_body_code='589', local_body_name='Unakoti alternate'),
            dict(state_code='99', local_body_code='589', local_body_name='Wrong state'),
            dict(village, local_body_code='4', local_body_name='Missing',
                 district_panchayat_code='999', intermediate_panchayat_code='999'),
            dict(village, local_body_code='5', local_body_name='No supplied parents',
                 district_panchayat_code='0', intermediate_panchayat_code=''),
        ])
        create(self.db, 'pri_local_bodies', [
            dict(state_code='16', local_body_code='589', local_body_name='Unakoti'),
            dict(state_code='16', local_body_code='589', local_body_name='Unakoti alternate'),
            dict(state_code='16', local_body_code='2886', local_body_name='Gournagar'),
            dict(state_code='99', local_body_code='2886', local_body_name='Wrong state'),
            dict(state_code='16', local_body_code='0', local_body_name='Invented parent'),
            dict(state_code='16', local_body_code='', local_body_name='Invented parent'),
        ])
        module = queries.get('traditional_local_bodies')
        self.assertEqual(module.required_datasets(), ('traditional_local_bodies',))
        for field in ('district_panchayat_name', 'intermediate_panchayat_name'):
            self.assertEqual(module.required_datasets(field=field),
                             ('traditional_local_bodies', 'pri_local_bodies'))
            self.assertEqual(module.search(self.db, 'Wrong state', field=field).fetchall(), [])
            self.assertEqual(module.search(self.db, 'Invented', field=field).fetchall(), [])
            self.assertEqual(module.search(self.db, 'Missing', field=field).fetchall(), [])
        for field, name in [('district_panchayat_name', 'Tribal Council'),
                            ('intermediate_panchayat_name', 'Ambassa Bac')]:
            result = records(module.search(self.db, name, field=field, mode='exact'))
            self.assertEqual([r['local_body_code'] for r in result], ['253794'])
        result = records(module.search(self.db, 'Unakoti', field='district_panchayat_name', mode='exact'))
        self.assertEqual([r['local_body_code'] for r in result], ['253927', '253927'])
        self.assertEqual(result[0]['lookup_names'], ['Unakoti', 'Unakoti alternate'])
        self.assertEqual(result[0]['district_panchayat_code'], '589')
        self.assertEqual(result[0]['local_body_name'], 'Deoracherra')
        result = records(module.search(self.db, 'Gournagar', field='intermediate_panchayat_name'))
        self.assertEqual([r['local_body_code'] for r in result], ['253927', '253927'])
        result = records(module.search(self.db, 'Unakot', field='district_panchayat_name',
                                        mode='fuzzy', max_distance=1, state_code='16', limit=1))
        self.assertEqual((result[0]['local_body_code'], result[0]['distance']), ('253927', 1))
        self.assertEqual(len(module.list(self.db).fetchall()), 10)

    def test_location_lookup_checks_type_unit_organization_and_central_scope(self):
        create(self.db,'central_org_units',[dict(organization_unit_code='7',organization_unit_name='Unit',
                    organization_code='5',entity_type='-5',entity_code='10')])
        base=dict(organization_unit_code='7',organization_code='5',entity_type='-5',entity_code='10',state_code='0')
        create(self.db,'org_unit_details',[dict(base,entity_name='Correct'),
                    dict(base,entity_name='Wrong type',entity_type='-6'),
                    dict(base,entity_name='Wrong scope',state_code='32'),
                    dict(base,entity_name='Wrong organization',organization_code='6')])
        module=queries.get('central_org_units')
        result=records(module.search(self.db,'Correct',field='entity_name'))
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['lookup_names'],['Correct'])
        self.assertEqual(module.search(self.db,'Wrong',field='entity_name').fetchall(),[])

    def test_event_dates_duplicates_and_polymorphic_entity_namespace(self):
        row=dict(entity_code='5',entity_name='Old name',entity_type='Village',report_date=date(2024,1,1))
        create(self.db,'changes',[row,row,dict(row,entity_type='District'),
                                  dict(row,report_date=date(2024,1,2))])
        changes=queries.get('changes')
        self.assertEqual(len(changes.by_code(self.db,5,entity_type='Village').fetchall()),3)
        self.assertEqual(len(changes.list(self.db,since='2024-01-01',until='2024-01-01').fetchall()),3)
        self.assertEqual(len(changes.list(self.db,since=date(2024,1,2)).fetchall()),1)
        with self.assertRaises(ValueError): changes.by_code(self.db,5)
        row=dict(transaction_id='0005',description='Village A and district B',state_code='0',
                 transaction_date=date(2024,1,1))
        create(self.db,'transactions',[row,row])
        transactions=queries.get('transactions')
        self.assertEqual(len(transactions.by_id(self.db,'0005',state_code=0).fetchall()),2)
        self.assertEqual(len(transactions.search(self.db,'district B').fetchall()),2)
        self.assertEqual(transactions.by_id(self.db,'5').fetchall(),[])
        self.db.sql("UPDATE changes SET census_code='null'")
        self.assertEqual(len(changes.list(self.db,census_code='null').fetchall()),4)


class QueryValidationTests(unittest.TestCase):
    def test_bad_inputs_fail_before_sql(self):
        db=Mock()
        for name in SCHEMAS:
            module=queries.get(name)
            lookup = module.by_id if name == 'transactions' else module.by_code
            with self.subTest(dataset=name), self.assertRaises(ValueError):
                lookup(db, None)
            for year in module.census_years:
                with self.subTest(dataset=name, year=year), self.assertRaises(ValueError):
                    module.by_census_code(db, None, year=year)
            for call in (lambda: module.list(db,imaginary_code='1'),
                         lambda: module.search(db,'name',field='name; DROP TABLE states'),
                         lambda: module.search(db,'name',metric='execute'),
                         lambda: module.search(db,'name',limit=0)):
                with self.subTest(dataset=name),self.assertRaises(ValueError): call()
        transactions=queries.get('transactions')
        for options in ({'since':'2024-99-01'},{'since':'20240101'},
                        {'since':'2024-01-02','until':'2024-01-01'}):
            with self.assertRaises(ValueError): transactions.list(db,**options)
        with self.assertRaises(ValueError): queries.get('arbitrary.module')
        db.sql.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class ReportCLIIntegrationTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.server=PublicFiles()
        entries={}
        with duckdb.connect() as db:
            create(db,'constituencies_mapping_pri',[dict(village_code='1',village_name='Village',state_code='32')])
            db.sql("CREATE TABLE states AS SELECT '32' AS state_code, 'Kerala' AS state_name")
            create(db,'transactions',[dict(transaction_id='01',description='Renamed village',
                                           state_code='32',transaction_date=date(2024,1,1))])
            for name in ('constituencies_mapping_pri','states','transactions'):
                path=self.root/f'{name}.parquet'
                db.sql(f'COPY {name} TO ? (FORMAT PARQUET)',params=[str(path)])
                entries[name]=self.server.dataset(name,path.read_bytes())
        self.index=self.server.index(entries)
        self.enterContext(patch('lgd_query._http.urlopen',side_effect=self.server.open))

    def run_cli(self,*args,format='json'):
        output=io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(['--metadata-url',INDEX,*args,'--cache-dir',str(self.root/'cache'),
                                       '--format',format]),0)
        return json.loads(output.getvalue()) if format=='json' else output.getvalue()

    def test_cli_fetches_name_dependency_only_when_needed_and_reuses_cache(self):
        result=self.run_cli('constituencies_mapping_pri','code','1')
        self.assertEqual(len(result['rows']),1)
        self.assertEqual(len(self.server.requests),2)
        result=self.run_cli('constituencies_mapping_pri','search','kerla','--field','state_name','--mode','fuzzy')
        self.assertEqual(result['rows'][0][-2:], [['Kerala'],1])
        self.assertEqual(len(self.server.requests),4)
        self.run_cli('constituencies_mapping_pri','search','Kerala','--field','state_name')
        self.assertEqual(len(self.server.requests),5)

    def test_cli_traditional_parent_search_loads_both_body_registers(self):
        import duckdb
        with duckdb.connect() as db:
            create(db, 'traditional_local_bodies', [
                dict(state_code='16', local_body_code='6918', local_body_name='Ambassa Bac'),
                dict(state_code='16', local_body_code='253794', local_body_name='Bagmara',
                     intermediate_panchayat_code='6918'),
                dict(state_code='16', local_body_code='253927', local_body_name='Deoracherra',
                     intermediate_panchayat_code='2886', district_panchayat_code='589'),
            ])
            create(db, 'pri_local_bodies', [
                dict(state_code='16', local_body_code='2886', local_body_name='Gournagar'),
                dict(state_code='16', local_body_code='589', local_body_name='Unakoti'),
            ])
            entries = {}
            for name in ('traditional_local_bodies', 'pri_local_bodies'):
                path = self.root/f'{name}.parquet'
                db.sql(f'COPY {name} TO ? (FORMAT PARQUET)', params=[str(path)])
                entries[name] = self.server.dataset(name, path.read_bytes())
            self.server.index(entries)
        self.run_cli('traditional_local_bodies', 'list')
        self.assertEqual(len(self.server.requests), 2)  # Index and TLB only.
        for field, name, body in [('intermediate_panchayat_name', 'Ambassa', '253794'),
                                  ('intermediate_panchayat_name', 'Gournagar', '253927'),
                                  ('district_panchayat_name', 'Unakoti', '253927')]:
            result = self.run_cli('traditional_local_bodies', 'search', name, '--field', field)
            self.assertEqual([r[result['columns'].index('local_body_code')] for r in result['rows']], [body])
        self.assertEqual(len(self.server.requests), 6)  # One PRI download, three indices.
        entries['pri_local_bodies']['daily']['observed_on'] = '2026-10-22'
        self.server.index(entries)
        before = len(self.server.requests)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_cli('traditional_local_bodies', 'search', 'Unakoti',
                         '--field', 'district_panchayat_name', '--observed-on', '2026-10-23')
        self.assertEqual(self.server.requests[before:], [INDEX])

    def test_explicit_date_guard_checks_every_dependency(self):
        self.index['datasets']['states']['daily']['observed_on']='2026-10-22'
        self.server.index(self.index['datasets'])
        release=Release.from_dict(self.index)
        inputs=queries.sources(release,'constituencies_mapping_pri',field='state_name')
        self.assertEqual([d.name for d in inputs],['constituencies_mapping_pri','states'])
        with self.assertRaises(ValueError):
            queries.sources(release,'constituencies_mapping_pri',field='state_name',observed_on='2026-10-23')
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('constituencies_mapping_pri','search','Kerala','--field','state_name',
                         '--observed-on','2026-10-23')
        self.assertEqual(self.server.requests,[INDEX])

    def test_unavailable_reference_fails_before_downloading_primary(self):
        self.index['datasets']['states']={'outcome':{'status':'unavailable','reason':'No source'}}
        self.server.index(self.index['datasets'])
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('constituencies_mapping_pri','search','Kerala','--field','state_name')
        self.assertEqual(self.server.requests,[INDEX])

    def test_each_report_cli_uses_its_own_identifiers_and_filters(self):
        import duckdb
        with duckdb.connect() as db:
            for name,schema in SCHEMAS.items():
                with self.subTest(dataset=name):
                    module=queries.get(name)
                    spec=module._queries.spec
                    row={column: (1 if kind=='INTEGER' else date(2024,1,1) if kind=='DATE'
                                  else '001' if column.endswith('_code') else 'Alpha')
                         for column,kind in schema.items()}
                    row[spec.primary_code]='001'
                    row[spec.primary_name]='Alpha'
                    create(db,name,[row])
                    path=self.root/f'{name}.parquet'
                    db.sql(f'COPY {name} TO ? (FORMAT PARQUET)',params=[str(path)])
                    self.server.index({name:self.server.dataset(name,path.read_bytes())})
                    self.assertEqual(len(self.run_cli(name,'list')['rows']),1)
                    action='id' if name=='transactions' else 'code'
                    scope=['--entity-type','Alpha'] if spec.typed_code else []
                    self.assertEqual(len(self.run_cli(name,action,'001',*scope)['rows']),1)
                    self.assertEqual(len(self.run_cli(name,'search','alpha','--mode','exact')['rows']),1)
                    for year in module.census_years:
                        self.assertEqual(len(self.run_cli(name,'census-code','001','--year',str(year))['rows']),1)

    def test_events_cli_uses_id_and_inclusive_date_filters(self):
        self.assertEqual(len(self.run_cli('transactions','id','01','--state-code','32')['rows']),1)
        self.assertEqual(self.run_cli('transactions','list','--since','2024-01-02')['rows'],[])
        self.assertEqual(len(self.run_cli('transactions','search','village','--until','2024-01-01')['rows']),1)

    @unittest.skipUnless(importlib.util.find_spec('rich'),'Rich is optional')
    def test_lookup_table_output(self):
        self.assertIn('Kerala',self.run_cli('constituencies_mapping_pri','search','Kerala',
                                          '--field','state_name',format='table'))


if __name__ == '__main__':
    unittest.main()
