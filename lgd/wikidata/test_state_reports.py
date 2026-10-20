import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import check_states
import common
from filters import filter_state
from raw_wikidata import write_records
from test_division_reports import entity, item


CAPITAL_DISTRICT_OR_TERRITORY = 395994


class StateReportTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        previous = Path.cwd()
        os.chdir(directory)
        self.addCleanup(os.chdir, previous)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch('requests.sessions.Session.request',
                                side_effect=AssertionError('Unexpected network request')))
        self.enterContext(patch.object(common, 'page_cache', {
            qid: {'id': f'Q{qid}', 'label': label}
            for qid, label in {
                common.UT_ID: 'union territory of India',
                common.STATE_ID: 'state of India',
                CAPITAL_DISTRICT_OR_TERRITORY: 'capital district or territory',
                56061: 'administrative territorial entity',
            }.items()
        }))
        Path('data/lgd').mkdir(parents=True)

    def report(self, types, qid='Q9357528'):
        label = 'National Capital Territory of Delhi' if qid == 'Q9357528' else 'Example state'
        write_records(Path('data/states.jsonl'), {
            qid: entity(qid, label, {
                'P31': [item(kind) for kind in types],
                'P17': [item(common.INDIA_ID)],
                'P131': [item(common.INDIA_ID)],
                common.P_LGD_STATE_CODE: ['7'],
            }),
        })
        Path('data/lgd/states.csv').write_text(
            f'State Code,State Name (In English)\n7,{label}\n')
        runpy.run_path(check_states.__file__, run_name='__main__')
        return json.loads(Path('reports/states.json').read_text())

    def test_delhi_accepts_its_union_territory_and_capital_territory_types(self):
        for types in [
            [common.UT_ID],
            [common.UT_ID, CAPITAL_DISTRICT_OR_TERRITORY],
            [CAPITAL_DISTRICT_OR_TERRITORY, common.UT_ID],
        ]:
            with self.subTest(types=types):
                self.assertTrue(all(not rows for rows in self.report(types).values()))

    def test_unexpected_delhi_types_remain_reported(self):
        for types in [
            [common.UT_ID, CAPITAL_DISTRICT_OR_TERRITORY, 56061],
            [common.UT_ID, 56061],
            [common.STATE_ID, CAPITAL_DISTRICT_OR_TERRITORY],
        ]:
            with self.subTest(types=types):
                rows = self.report(types)['multiple_instance_of']
                self.assertEqual([row['wikidata_id'] for row in rows], ['Q9357528'])
                self.assertEqual(
                    [entry['id'] for entry in rows[0]['inst_of_entries']],
                    [f'Q{kind}' for kind in types],
                )

    def test_other_states_do_not_inherit_delhis_exception(self):
        rows = self.report([common.UT_ID, CAPITAL_DISTRICT_OR_TERRITORY],
                           qid='Q1174')['multiple_instance_of']
        self.assertEqual([row['wikidata_id'] for row in rows], ['Q1174'])

    def test_base_checker_remains_strict_without_the_state_exception(self):
        self.report([common.UT_ID, CAPITAL_DISTRICT_OR_TERRITORY])
        report = common.base_entity_checks(
            has_lgd=False, wd_fname='data/states.jsonl', wd_filter_fn=filter_state,
            check_expected_located_in_fn=lambda _: {'ok': True},
        )
        self.assertEqual([row['wikidata_id'] for row in report['multiple_instance_of']],
                         ['Q9357528'])


if __name__ == '__main__':
    unittest.main()
