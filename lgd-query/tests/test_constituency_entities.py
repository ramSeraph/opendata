"""Typed coverage references, alternative registers and CLI dependency loading."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from lgd_query import Release, cli
from lgd_query.queries import constituency_coverage as coverage
from test_dataset_queries import create, records
from test_reader import INDEX, PublicFiles


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class CoverageEntityTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db=duckdb.connect()
        self.addCleanup(self.db.close)

    def test_typed_lookup_uses_codes_and_state_preserving_contradictory_claims(self):
        row=dict(entity_code='001',entity_name='Old label',entity_type='SubDistrict',state_code='10',
                 parliament_constituency_code='191',assembly_constituency_code='1349',coverage_type='Fully Covered')
        create(self.db,'constituency_coverage',[row,row,dict(row,coverage_type='Partly Covered'),
            dict(row,entity_type='District'),dict(row,entity_code='999')])
        self.db.sql("""CREATE TABLE subdistricts AS SELECT * FROM (VALUES
            ('001','New register label','10','101'),('001','Wrong state','11','102'),
            ('1','Different leading zeros','10','103')) AS x(subdistrict_code,subdistrict_name,state_code,district_code)""")
        result=records(coverage.entities(self.db,entity_type='SubDistrict',entity_code='001'))
        self.assertEqual(len(result),1)
        self.assertEqual((result[0]['entity_dataset'],result[0]['entity_name'],result[0]['district_code']),
                         ('subdistricts','New register label','101'))
        self.assertEqual(len(coverage.by_code(self.db,'001',entity_type='SubDistrict').fetchall()),3)
        self.assertEqual(len(coverage.entities(self.db,entity_type='SubDistrict',coverage_type='Partly Covered').fetchall()),1)
        self.assertEqual(coverage.entities(self.db,entity_type='SubDistrict',entity_code=1).fetchall(),[])
        self.assertEqual(coverage.entities(self.db,entity_type='SubDistrict',entity_code='999').fetchall(),[])
        self.assertEqual(len(coverage.by_code(self.db,'999',entity_type='SubDistrict').fetchall()),1)
        self.assertEqual(coverage.entities(self.db,entity_type='SubDistrict',entity_name="' OR TRUE --").fetchall(),[])
        self.assertEqual(len(coverage.entities(self.db,entity_type='SubDistrict',assembly_constituency_code=1349).fetchall()),1)

    def test_village_categories_and_actual_reference_duplicates_survive(self):
        row=dict(entity_code='100',entity_name='Reported',entity_type='Village',state_code='32')
        create(self.db,'constituency_coverage',[row,row])
        rural=dict(village_code='100',village_name='Reference',state_code='32',village_category='R')
        create(self.db,'villages',[rural,rural,dict(rural,village_category='U'),
                                  dict(rural,village_code='101')])
        result=records(coverage.entities(self.db,entity_type='Village'))
        self.assertEqual(sorted(r['village_category'] for r in result),['R','R','U'])
        self.assertEqual({r['entity_dataset'] for r in result},{'villages'})

    def test_normalized_conflict_remains_queryable_without_choosing_a_flag(self):
        row=dict(entity_code='1013',entity_name='Sidhaw',entity_type='SubDistrict',state_code='10',
                 parliament_constituency_code='191',assembly_constituency_code='1349',coverage_type=None)
        create(self.db,'constituency_coverage',[row])
        self.db.sql("CREATE TABLE subdistricts AS SELECT '1013' subdistrict_code, 'Sidhaw' subdistrict_name, '10' state_code")
        self.assertEqual(len(coverage.list(self.db).filter('coverage_type IS NULL').fetchall()),1)
        self.assertEqual(len(coverage.entities(self.db,entity_type='SubDistrict',entity_code='1013').fetchall()),1)
        for flag in ('Fully Covered','Partly Covered'):
            self.assertEqual(coverage.list(self.db,coverage_type=flag).fetchall(),[])

    def test_body_lookup_searches_all_three_registers_and_retains_variants(self):
        row=dict(entity_code='7',entity_name='Body',entity_type='Localbody',state_code='16')
        create(self.db,'constituency_coverage',[row,row,dict(row,entity_type='Village'),
            dict(row,entity_code='0'),dict(row,entity_code='')])
        for source in ('urban_local_bodies','pri_local_bodies','traditional_local_bodies'):
            create(self.db,source,[dict(local_body_code='7',local_body_name=source,state_code='16'),
                                  dict(local_body_code='7',local_body_name='Wrong state',state_code='17'),
                                  dict(local_body_code='0',local_body_name='No supplied code',state_code='16')])
        result=records(coverage.entities(self.db,entity_type='Localbody'))
        self.assertEqual({r['entity_dataset'] for r in result},
                         {'urban_local_bodies','pri_local_bodies','traditional_local_bodies'})
        self.assertEqual(len(result),3)
        self.assertTrue(all(r['entity_code']=='7' for r in result))
        self.assertIn('parent_local_body_code',result[0])
        self.assertIn('intermediate_panchayat_code',result[0])
        self.assertIn('local_body_census_2011_code',result[0])

    def test_wards_resolve_urban_and_pri_registers(self):
        row=dict(entity_code='7',entity_name='Ward',entity_type='Ward',state_code='32')
        create(self.db,'constituency_coverage',[row,row])
        for source in ('urban_local_body_wards','pri_local_body_wards'):
            create(self.db,source,[dict(ward_code='7',ward_name=source,state_code='32',local_body_code='9')])
        result=records(coverage.entities(self.db,entity_type='Ward'))
        self.assertEqual(len(result),2)
        self.assertEqual({r['entity_dataset'] for r in result},{'urban_local_body_wards','pri_local_body_wards'})
        self.assertTrue(all(r['local_body_code']=='9' for r in result))

    def test_types_are_validated_before_sql_and_dependencies_are_explicit(self):
        db=Mock()
        for invalid in ('district','Unknown',None,[],"Village'; DROP TABLE districts; --"):
            with self.assertRaises(ValueError):coverage.entities(db,entity_type=invalid)
            with self.assertRaises(ValueError):coverage.required_entity_datasets(invalid)
        db.sql.assert_not_called()
        self.assertEqual(coverage.required_entity_datasets('District'),('constituency_coverage','districts'))
        self.assertEqual(coverage.required_entity_datasets('Ward'),
                         ('constituency_coverage','urban_local_body_wards','pri_local_body_wards'))
        self.assertEqual(coverage.required_datasets(),('constituency_coverage',))
        release=Mock()
        coverage.entity_sources(release,'Ward',observed_on='2026-10-23')
        self.assertEqual([call.args[0] for call in release.dataset.call_args_list],
                         ['constituency_coverage','urban_local_body_wards','pri_local_body_wards'])
        self.assertTrue(all(call.kwargs['observed_on']=='2026-10-23' for call in release.dataset.call_args_list))


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class CoverageEntityCLITests(unittest.TestCase):
    def setUp(self):
        import duckdb
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.server=PublicFiles()
        entries={}
        with duckdb.connect() as db:
            row=dict(entity_code='1013',entity_name='Sidhaw',entity_type='SubDistrict',state_code='10',
                     coverage_type='Fully Covered',assembly_constituency_code='1349')
            create(db,'constituency_coverage',[row,dict(row,coverage_type='Partly Covered')])
            db.sql("CREATE TABLE subdistricts AS SELECT '1013' subdistrict_code,'Sidhaw' subdistrict_name,'10' state_code,'203' district_code")
            db.sql("CREATE TABLE districts AS SELECT '1013' district_code,'Other namespace' district_name,'10' state_code")
            for name in ('constituency_coverage','subdistricts','districts'):
                path=self.root/(name+'.parquet')
                db.sql(f'COPY {name} TO ? (FORMAT PARQUET)',params=[str(path)])
                entries[name]=self.server.dataset(name,path.read_bytes())
        self.index=self.server.index(entries)
        self.enterContext(patch('lgd_query._http.urlopen',side_effect=self.server.open))

    def run_cli(self,*args,format='json'):
        output=io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(['--metadata-url',INDEX,'constituency_coverage','entities',*args,
                '--cache-dir',str(self.root/'cache'),'--format',format]),0)
        return json.loads(output.getvalue()) if format=='json' else output.getvalue()

    def test_cli_resolves_only_selected_type_and_supports_json_and_tables(self):
        result=self.run_cli('--entity-type','SubDistrict','--entity-code','1013')
        self.assertEqual(len(result['rows']),1)
        self.assertEqual(result['rows'][0][:4],['subdistricts','SubDistrict','1013','Sidhaw'])
        self.assertEqual(len(self.server.requests),3)
        self.assertIn('Sidhaw',self.run_cli('--entity-type','SubDistrict',format='table'))
        self.assertEqual(len(self.server.requests),4)  # cached files; only metadata refreshed
        result=self.run_cli('--entity-type','District','--entity-code','1013')
        self.assertEqual(result['rows'],[])  # no District claim selects the same numeric code

    def test_every_reference_must_be_available_and_satisfy_date_guard(self):
        self.index['datasets']['subdistricts']['daily']['observed_on']='2026-10-22'
        self.server.index(self.index['datasets'])
        with self.assertRaises(ValueError):
            coverage.entity_sources(Release.from_dict(self.index),'SubDistrict',observed_on='2026-10-23')
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('--entity-type','SubDistrict','--observed-on','2026-10-23')
        self.assertEqual(self.server.requests,[INDEX])
        self.index['datasets']['subdistricts']={'outcome':{'status':'unavailable','reason':'No source'}}
        self.server.index(self.index['datasets'])
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('--entity-type','SubDistrict')
        self.assertEqual(self.server.requests,[INDEX,INDEX])


if __name__=='__main__':unittest.main()
