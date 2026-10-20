import contextlib
import csv
import io
import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_district_panchayats as checker
import common
import constants
from raw_wikidata import read_records, write_records
from test_division_reports import entity, item


class DistrictPanchayatReportTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        previous = Path.cwd()
        os.chdir(directory)
        self.addCleanup(os.chdir, previous)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(common, 'page_cache', None))
        self.enterContext(patch.object(checker, 'g_wd_state_map_rev', None))
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('Unexpected network request')))
        Path('data/lgd').mkdir(parents=True)
        write_records(Path('data/states.jsonl'), {
            'Q1498': entity('Q1498', 'Uttar Pradesh', {
                'P31': [item(constants.STATE_ID)], 'P12747': ['9'], 'P1366': [item(1499)],
            }),
            'Q1174': entity('Q1174', 'Haryana', {
                'P31': [item(constants.STATE_ID)], 'P12747': ['6'],
            }),
        })
        write_records(Path('data/districts.jsonl'), {
            'Q2001': entity('Q2001', 'Known district', {
                'P31': [item(constants.DIST_ID)], 'P12746': ['100'],
            }),
            'Q2002': entity('Q2002', 'Unmapped district', {
                'P31': [item(constants.DIST_ID)],
            }),
        })
        write_records(Path('data/district_panchayats.jsonl'), {
            f'Q{qid}': entity(f'Q{qid}', f'Example {code}', {
                'P31': [item(constants.DIST_COUNCIL_OF_INDIA_ID)],
                'P17': [item(constants.INDIA_ID)],
                'P131': [item(parent)],
                constants.P_LGD_LOCAL_BODY_CODE: [code],
                constants.P_TERRITORY_OVERLAPS: [item(2002)],
            }) for qid, code, parent in [(4001, '101', 1498), (4002, '102', 1498), (4003, '103', 1174)]
        })
        fields = ['Localbody Code', 'Localbody Name (In English)', 'Localbody Type Code', 'State Code', 'State Name']
        with Path(checker.lgd_fname).open('w') as stream:
            writer = csv.writer(stream)
            writer.writerow(fields)
            writer.writerows([
                ['101', 'Example 101', '1', '9', 'Uttar Pradesh'],
                ['102', 'Example 102', '1', '6', 'Haryana'],
                ['103', 'Example 103', '1', '6', 'Haryana'],
                ['104', 'Missing UP panchayat', '1', '9', 'Uttar Pradesh'],
            ])
        Path('data/lgd/district_panchayats.csv').write_text(
            'District Panchayat Code,Disrict Code\n101,100\n101,790\n102,100\n103,100\n')
        Path('data/lgd/districts.csv').write_text(
            'District Code,District Name(In English)\n100,Known district\n790,Unmapped district\n')

    def test_unresolved_state_is_reported_and_other_hierarchies_still_checked(self):
        rows = checker.hierarchy_check()['wrong_hierarchy']
        self.assertEqual([row['wikidata_id'] for row in rows], ['Q4001', 'Q4002'])
        self.assertEqual(rows[0]['unresolved_state_code'], '9')
        self.assertIn('Uttar Pradesh', rows[0]['expected'][0]['label'])
        self.assertNotIn('id', rows[0]['expected'][0])
        self.assertEqual(rows[1]['expected'][0]['id'], 'Q1174')

    def test_missing_parent_does_not_generate_a_guessed_correction(self):
        entry = {'State Code': '9', 'State Name': 'Uttar Pradesh', 'lgd_name': 'Example', 'lgd_code': '104'}
        correction = checker.get_correction_info(entry)
        self.assertIsNone(correction['loc_in'])
        self.assertEqual(correction['unresolved_parent'], 'Uttar Pradesh (LGD state 9)')
        entry.update({'State Code': '6', 'State Name': 'Haryana'})
        correction = checker.get_correction_info(entry)
        self.assertEqual(correction['loc_in'], 'Q1174')
        self.assertNotIn('unresolved_parent', correction)

    def test_unresolved_district_does_not_make_current_overlap_look_extra(self):
        rows = checker.territory_overlaps_check()['mismatch_territory_overlaps']
        unresolved = next(row for row in rows if row['wikidata_id'] == 'Q4001')
        self.assertEqual(unresolved['unresolved'][0]['lgd_code'], '790')
        self.assertEqual([row['id'] for row in unresolved['missing']], ['Q2001'])
        self.assertEqual(unresolved['extra'], [])
        resolved = next(row for row in rows if row['wikidata_id'] == 'Q4002')
        self.assertNotIn('unresolved', resolved)
        self.assertEqual([row['id'] for row in resolved['extra']], ['Q2002'])

    def test_complete_report_is_written_with_unresolved_parents(self):
        runpy.run_path(checker.__file__, run_name='__main__')
        report = json.loads(Path('reports/district_panchayats.json').read_text())
        self.assertEqual(len(report['missing']), 1)
        self.assertIsNone(report['missing'][0]['correction_info']['loc_in'])
        self.assertEqual(report['wrong_hierarchy'][0]['unresolved_state_code'], '9')
        self.assertEqual(len(report['mismatch_territory_overlaps']), 3)

    def test_suffix_is_selected_from_the_parent_state(self):
        rows = checker.suffix_check()['wrong_suffix']
        self.assertEqual([row['wikidata_id'] for row in rows], ['Q4003'])
        self.assertEqual(rows[0]['expected_suffix'], constants.state_info['6']['dp_suffix'])
        records = read_records(Path(checker.wd_fname))
        records['Q4003']['labels']['en']['value'] += ' ' + rows[0]['expected_suffix']
        write_records(Path(checker.wd_fname), records)
        self.assertEqual(checker.suffix_check()['wrong_suffix'], [])


if __name__ == '__main__':
    unittest.main()
