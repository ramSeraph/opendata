"""Dated report views, code namespaces, ambiguous mappings and CLI loading."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from lgd_query import cli
from lgd_query.queries import constituencies_mapping_pri as pri
from lgd_query.queries import constituencies_mapping_urban as urban
from test_dataset_queries import create, records
from test_reader import INDEX, PublicFiles


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class EciLookupTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db=duckdb.connect()
        self.addCleanup(self.db.close)

    def test_both_levels_and_reports_preserve_names_zeros_and_deduplicate_paths(self):
        row=dict(village_code='1',local_body_code='2',ward_code='3',state_code='09',
                 parliament_constituency_code='001',parliament_constituency_eci_code='01',
                 parliament_constituency_name='Parliament',assembly_constituency_code='010',
                 assembly_constituency_eci_code='02',assembly_constituency_name='Assembly')
        for module in (pri,urban):
            source=module._queries.spec.dataset
            create(self.db,source,[row,row,dict(row,local_body_code='9',assembly_constituency_name='Alternative'),
                                  dict(row,state_code='10')])
            for level in module.eci_levels:
                field=level+'_constituency_code'
                result=records(module.eci_codes(self.db,level=level,constituency_code=row[field],state_code='09'))
                self.assertEqual(len(result),1)
                self.assertEqual(result[0]['source_dataset'],source)
                self.assertEqual(result[0][level+'_constituency_eci_code'],row[level+'_constituency_eci_code'])
                self.assertFalse(result[0]['conflicting_eci_codes'])
                self.assertFalse(result[0]['eci_code_reused'])
            self.assertEqual(result[0]['lookup_names'],['Alternative','Assembly'])
            self.assertEqual(module.eci_codes(self.db,level='assembly',constituency_code=10).fetchall(),[])
            self.assertEqual(len(module.list(self.db).fetchall()),4)

    def test_filtering_does_not_hide_competing_codes_or_reverse_ambiguity(self):
        row=dict(state_code='6',assembly_constituency_code='416',assembly_constituency_name='Name',
                 assembly_constituency_eci_code='42')
        create(self.db,'constituencies_mapping_pri',[row,dict(row,assembly_constituency_eci_code='43'),
            dict(row,assembly_constituency_code='419'),dict(row,state_code='7',assembly_constituency_code='420')])
        result=records(pri.eci_codes(self.db,level='assembly',constituency_code=416,state_code=6,eci_code=42))
        self.assertEqual(len(result),1)
        self.assertTrue(result[0]['conflicting_eci_codes'])
        self.assertTrue(result[0]['eci_code_reused'])
        self.assertEqual(len(pri.eci_codes(self.db,level='assembly',eci_code='42').fetchall()),3)
        result=records(pri.eci_codes(self.db,level='assembly',state_code=7,eci_code=42))
        self.assertFalse(result[0]['eci_code_reused'])
        result=records(pri.eci_codes(self.db,level='assembly',state_code=6,eci_code=43))
        self.assertTrue(result[0]['conflicting_eci_codes'])
        self.assertFalse(result[0]['eci_code_reused'])

    def test_missing_codes_are_not_invented_and_empty_results_have_columns(self):
        row=dict(state_code='9',parliament_constituency_code='1',parliament_constituency_eci_code='2')
        rows=[dict(row,**{field:value}) for field in ('state_code','parliament_constituency_code','parliament_constituency_eci_code')
              for value in (None,'','0',' ')]
        create(self.db,'constituencies_mapping_pri',rows)
        result=pri.eci_codes(self.db,level='parliament')
        self.assertEqual(result.fetchall(),[])
        self.assertIn('parliament_constituency_eci_code',result.columns)
        self.assertEqual(len(pri.list(self.db).fetchall()),12)

    def test_invalid_inputs_fail_before_sql(self):
        db=Mock()
        for level in (None,[],"assembly; DROP TABLE states",'Assembly'):
            with self.assertRaises(ValueError):pri.eci_codes(db,level=level)
        for field in ('constituency_code','state_code','eci_code'):
            for value in (True,-1,'1 OR TRUE','１２',''):
                with self.assertRaises(ValueError):pri.eci_codes(db,level='assembly',**{field:value})
        db.sql.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec('duckdb'), 'DuckDB is optional')
class EciCLITests(unittest.TestCase):
    def setUp(self):
        import duckdb
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        path=self.root/'pri.parquet'
        with duckdb.connect() as c:
            create(c,'constituencies_mapping_pri',[dict(state_code='6',assembly_constituency_code='416',
                assembly_constituency_name='Name',assembly_constituency_eci_code='42')])
            c.sql('SELECT * FROM constituencies_mapping_pri').write_parquet(str(path))
        self.server=PublicFiles()
        self.document=self.server.index(dict(constituencies_mapping_pri=self.server.dataset(
            'constituencies_mapping_pri',path.read_bytes(),observed='2022-10-12')))
        self.enterContext(patch('lgd_query._http.urlopen',side_effect=self.server.open))

    def run_cli(self,*options):
        output=io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(['--metadata-url',INDEX,'constituencies_mapping_pri','eci-codes',
                '--level','assembly','--constituency-code','416','--cache-dir',str(self.root/'cache'),*options]),0)
        return output.getvalue()

    def test_json_rich_cache_and_date_guard(self):
        result=json.loads(self.run_cli('--format','json','--observed-on','2022-10-12'))
        row=dict(zip(result['columns'],result['rows'][0]))
        self.assertEqual(row['assembly_constituency_eci_code'],'42')
        self.assertFalse(row['conflicting_eci_codes'])
        downloads=sum(url.endswith('.parquet') for url in self.server.requests)
        self.assertIn('42',self.run_cli('--format','table'))
        self.assertEqual(sum(url.endswith('.parquet') for url in self.server.requests),downloads)
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('--format','json','--observed-on','2026-10-24')
        self.assertEqual(sum(url.endswith('.parquet') for url in self.server.requests),downloads)

    def test_retired_unavailable_source_is_not_silently_replaced(self):
        self.server.index(dict(constituencies_mapping_pri=dict(outcome=dict(status='unavailable',reason='Historical only'))))
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.run_cli('--format','json')
        self.assertEqual(self.server.requests,[INDEX])


if __name__=='__main__':
    unittest.main()
