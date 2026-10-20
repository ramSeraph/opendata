import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_divisions
import common
import constants
from raw_wikidata import read_records, write_records


def entity(qid, label, claims):
    return {
        'id': qid,
        'labels': {'en': {'language': 'en', 'value': label}},
        'claims': {
            prop: [
                {'rank': 'normal', 'mainsnak': {'datavalue': {'value': value}}}
                for value in values
            ]
            for prop, values in claims.items()
        },
    }


def item(number):
    return {'id': f'Q{number}', 'numeric-id': number, 'entity-type': 'item'}


class DivisionReportTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        previous = Path.cwd()
        os.chdir(directory)
        self.addCleanup(os.chdir, previous)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(common, 'page_cache', None))
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
        self.divisions = {
            'Q1001': entity('Q1001', 'Example UP division', {
                'P31': [item(constants.DIV_ID)], 'P131': [item(1498)],
            }),
            'Q1002': entity('Q1002', 'Example Haryana division', {
                'P31': [item(constants.DIV_ID)], 'P131': [item(1174)],
            }),
        }
        write_records(Path('data/divisions.jsonl'), self.divisions)
        write_records(Path('data/districts.jsonl'), {
            'Q2001': entity('Q2001', 'Example Haryana district', {
                'P31': [item(constants.DIST_ID)], 'P12746': ['1'],
            }),
            'Q2002': entity('Q2002', 'Example UP district', {
                'P31': [item(constants.DIST_ID)], 'P12746': ['2'],
            }),
        })
        Path('data/lgd/states.csv').write_text(
            'State Code,State Name (In English)\n6,Haryana\n9,Uttar Pradesh\n')
        Path('data/lgd/districts.csv').write_text(
            'District Code,State Code,State Name (In English)\n1,6,Haryana\n2,9,Uttar Pradesh\n')

    def test_excluded_parent_is_reported_and_other_states_are_checked(self):
        hierarchy = check_divisions.hierarchy_check()['wrong_hierarchy']
        self.assertEqual([row['wikidata_id'] for row in hierarchy], ['Q1001'])
        self.assertEqual(hierarchy[0]['current'][0]['id'], 'Q1498')
        mismatches = check_divisions.contains_completeness_check()['mismatch_in_contains']
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]['parent']['id'], 'Q1174')
        self.assertEqual([row['id'] for row in mismatches[0]['missing']], ['Q2001'])

    def test_extra_district_identifies_division_that_contains_it(self):
        # A district from another state is incorrectly listed by this division.
        self.divisions['Q1002']['claims']['P150'] = [
            {'rank': 'normal', 'mainsnak': {'datavalue': {'value': item(2002)}}},
        ]
        write_records(Path('data/divisions.jsonl'), self.divisions)
        mismatches = check_divisions.contains_completeness_check()['mismatch_in_contains']
        self.assertEqual(mismatches[0]['extra'], [{
            'element': {'id': 'Q2002', 'label': 'Example UP district'},
            'child': {'id': 'Q1002', 'label': 'Example Haryana division'},
        }])

    def test_state_without_an_lgd_code_does_not_crash_dependent_checks(self):
        states = read_records(Path('data/states.jsonl'))
        del states['Q1174']['claims']['P12747']
        write_records(Path('data/states.jsonl'), states)
        self.assertEqual(check_divisions.inst_of_check()['wrong_inst_of'], [])
        self.assertEqual(check_divisions.contains_completeness_check()['mismatch_in_contains'], [])

    def test_district_without_an_lgd_code_does_not_crash_inverse_check(self):
        districts = read_records(Path('data/districts.jsonl'))
        del districts['Q2001']['claims']['P12746']
        write_records(Path('data/districts.jsonl'), districts)
        self.divisions['Q1002']['claims']['P150'] = [
            {'rank': 'normal', 'mainsnak': {'datavalue': {'value': item(2001)}}},
        ]
        write_records(Path('data/divisions.jsonl'), self.divisions)
        self.assertEqual(check_divisions.contains_inverse_check()['missing_contained_in'], [])


if __name__ == '__main__':
    unittest.main()
