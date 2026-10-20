import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_districts as checker
import common
import constants
from raw_wikidata import write_records
from test_division_reports import entity, item


class DistrictReportTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(contextlib.chdir(directory))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(common, 'page_cache', None))
        self.enterContext(patch.object(checker, 'g_wd_state_map_rev', None))
        self.enterContext(
            patch(
                'requests.sessions.Session.request',
                side_effect=AssertionError('Unexpected network request'),
            )
        )
        Path('data/lgd').mkdir(parents=True)
        write_records(
            Path('data/states.jsonl'),
            {
                f'Q{qid}': entity(
                    f'Q{qid}',
                    name,
                    {
                        'P31': [item(constants.STATE_ID)],
                        constants.P_LGD_STATE_CODE: [code],
                    },
                )
                for qid, name, code in [(1174, 'Haryana', '6'), (1498, 'Uttar Pradesh', '9')]
            },
        )
        write_records(
            Path('data/divisions.jsonl'),
            {
                'Q1001': entity(
                    'Q1001',
                    'Haryana division',
                    {
                        'P31': [item(constants.DIV_ID)],
                        'P131': [item(1174)],
                    },
                ),
            },
        )
        self.districts = {
            f'Q{qid}': entity(
                f'Q{qid}',
                f'District {code}',
                {
                    'P31': [item(constants.DIST_ID)],
                    'P131': [item(parent)],
                    constants.P_LGD_DIST_CODE: [code],
                },
            )
            for qid, code, parent in [(2001, '100', 1498), (2002, '200', 1174), (2003, '300', 1001)]
        }
        write_records(Path(checker.wd_fname), self.districts)
        Path(checker.lgd_fname).write_text(
            'District Code,District Name(In English),State Code,State Name (In English)\n'
            '100,Wrong parent,6,Haryana\n200,Direct parent,6,Haryana\n300,Via division,6,Haryana\n'
        )
        self.missing_district = {
            'lgd_code': '400',
            'lgd_name': 'Example',
            'State Code': '6',
            'State Name (In English)': 'Haryana',
            'Effective Date': '24Sep2025',
        }

    def test_correction_uses_a_real_district_qid(self):
        correction = checker.get_correction_info(self.missing_district)
        self.assertEqual(
            correction,
            {
                'label': 'Example district',
                'desc': 'district in Haryana, India',
                'inst_of': 'Q1149652',
                'loc_in': 'Q1174',
                'inception': '+2025-09-24T00:00:00Z/11',
                'lgd_code': '400',
                'lgd_code_prop': 'P12746',
            },
        )

    def test_hierarchy_uses_district_codes_and_accepts_divisions(self):
        rows = checker.hierarchy_check()['wrong_hierarchy']
        self.assertEqual([row['wikidata_id'] for row in rows], ['Q2001'])
        self.assertEqual(rows[0]['current'][0]['id'], 'Q1498')
        self.assertEqual(rows[0]['expected'][0]['id'], 'Q1174')

    def test_ambiguous_state_mapping_does_not_guess_a_correction(self):
        from raw_wikidata import read_records

        states = read_records(Path('data/states.jsonl'))
        states['Q9000'] = entity(
            'Q9000',
            'Duplicate Haryana',
            {
                'P31': [item(constants.STATE_ID)],
                constants.P_LGD_STATE_CODE: ['6'],
            },
        )
        write_records(Path('data/states.jsonl'), states)
        rows = checker.hierarchy_check()['wrong_hierarchy']
        self.assertEqual(len(rows), 3)
        self.assertEqual({row['unresolved_state_code'] for row in rows}, {'6'})
        self.assertNotIn('id', rows[0]['expected'][0])
        correction = checker.get_correction_info(self.missing_district)
        self.assertIsNone(correction['loc_in'])
        self.assertEqual(correction['unresolved_parent'], 'Haryana (LGD state 6)')

    def test_division_with_missing_or_multiple_parents_is_reported(self):
        for parents in [[], [item(1174), item(1498)]]:
            with self.subTest(parents=parents):
                write_records(
                    Path('data/divisions.jsonl'),
                    {
                        'Q1001': entity(
                            'Q1001',
                            'Ambiguous division',
                            {
                                'P31': [item(constants.DIV_ID)],
                                'P131': parents,
                            },
                        ),
                    },
                )
                rows = checker.hierarchy_check()['wrong_hierarchy']
                self.assertEqual([row['wikidata_id'] for row in rows], ['Q2001', 'Q2003'])
                self.assertEqual(rows[1]['current'][-1]['id'], 'Q1001')
                self.assertEqual(rows[1]['expected'][0]['id'], 'Q1174')


if __name__ == '__main__':
    unittest.main()
