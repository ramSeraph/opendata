import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import requests

import check_subdistricts as checker
import common
from raw_wikidata import write_records
from test_division_reports import entity, item


class SubdistrictReportTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        previous = Path.cwd()
        os.chdir(directory)
        self.addCleanup(os.chdir, previous)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(common, 'page_cache', None))
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('Unexpected network request')))
        Path('data/lgd').mkdir(parents=True)
        write_records(Path('data/districts.jsonl'), {
            f'Q{qid}': entity(f'Q{qid}', label, {'P31': [item(common.DIST_ID)], 'P12746': [code]})
            for qid, label, code in [(2001, 'Expected district', '100'), (2002, 'Other district', '200')]
        })
        write_records(Path('data/subdivisions.jsonl'), {})
        expected_type = int(common.state_info['6']['wd_id'][1:])
        wrong_type = int(common.state_info['9']['wd_id'][1:])
        write_records(Path('data/subdistrict_types.jsonl'), {
            f'Q{expected_type}': entity(f'Q{expected_type}', 'Haryana tehsil', {}),
            f'Q{wrong_type}': entity(f'Q{wrong_type}', 'UP tehsil', {}),
            **{alt['wd_id']: entity(alt['wd_id'], alt['name'], {}) for alt in common.state_info['6'].get('alts', [])},
        })
        write_records(Path('data/subdistricts.jsonl'), {
            f'Q{qid}': entity(f'Q{qid}', f'Subdistrict {code}', {
                'P31': [item(kind)], 'P131': [item(parent)], common.P_LGD_SUBDIST_CODE: [code],
            }) for qid, code, kind, parent in [(5001, '1', expected_type, 2002), (5002, '2', wrong_type, 2001), (5003, '3', expected_type, 2001)]
        })
        Path(checker.lgd_fname).write_text(
            'Sub-district Code,Sub-district Name,District Code,State Code\n'
            '1,Subdistrict 1,100,6\n2,Subdistrict 2,100,6\n3,Subdistrict 3,100,6\n')

    def test_hierarchy_uses_subdistrict_codes_and_finds_wrong_district(self):
        rows = checker.hierarchy_check()['wrong_hierarchy']
        self.assertEqual([row['wikidata_id'] for row in rows], ['Q5001'])
        self.assertEqual(rows[0]['current'][0]['id'], 'Q2002')
        self.assertEqual(rows[0]['expected'][0]['id'], 'Q2001')

    def test_type_check_uses_subdistrict_codes_and_finds_wrong_state_type(self):
        rows = checker.inst_of_check()['wrong_inst_of']
        self.assertEqual([row['wikidata_id'] for row in rows], ['Q5002'])
        self.assertEqual(rows[0]['expected_inst_ofs'][0]['id'], common.state_info['6']['wd_id'])

    def test_complete_report_survives_an_effective_date_http_failure(self):
        Path(checker.lgd_fname).write_text(
            'Sub-district Code,Sub-district Name,District Code,State Code,District Name,State Name\n'
            '1,Subdistrict 1,100,6,Expected district,Haryana\n'
            '2,Subdistrict 2,100,6,Expected district,Haryana\n'
            '3,Subdistrict 3,100,6,Expected district,Haryana\n'
            '4,Missing subdistrict,100,6,Expected district,Haryana\n')
        response = requests.Response()
        response.status_code = 503
        response.url = 'https://lgdirectory.gov.in/globalviewSubDistrictDetail.do?globalsubdistrictId=4'
        with patch.object(common.requests, 'get', return_value=response) as fetch, \
             patch.object(common.time, 'sleep'):
            runpy.run_path(checker.__file__, run_name='__main__')
        self.assertEqual(fetch.call_count, 3)
        report = json.loads(Path('reports/subdistricts.json').read_text())
        self.assertEqual(len(report['missing']), 1)
        missing = report['missing'][0]
        self.assertEqual(missing['lgd_entry']['lgd_code'], '4')
        self.assertIn('503', missing['lgd_entry']['Effective Date Error'])
        self.assertIsNone(missing['correction_info']['inception'])
        self.assertEqual([row['wikidata_id'] for row in report['wrong_hierarchy']], ['Q5001'])
        self.assertEqual([row['wikidata_id'] for row in report['wrong_inst_of']], ['Q5002'])


if __name__ == '__main__':
    unittest.main()
