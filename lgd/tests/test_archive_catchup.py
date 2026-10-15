import contextlib
from datetime import date
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from utils.archive_catchup import build_plan, publish_plan


class CatchupPlanTests(unittest.TestCase):
    TODAY = date(2026, 10, 16)
    FILES = [
        'villages.01Sep2026.csv.7z', 'villages.02Sep2026.csv.7z',
        'villages.01Nov2025.csv.7z', 'villages_by_blocks.01Nov2025.csv.7z',
        'states.01Sep2026.csv.7z', 'villages.01Oct2026.csv.7z',
        'villages.01Nov2026.csv.7z', 'changes.csv.7z', 'transactions.csv.7z',
        'changes_dates_covered.txt', 'listing_files.csv', 'villages.Sep2026.7z',
    ]

    def test_finds_closed_month_leftovers_oldest_first_ignoring_other_assets(self):
        self.assertEqual(build_plan(self.FILES, today=self.TODAY), [
            {'month': 'Nov2025', 'component': 'villages', 'snapshots': 1},
            {'month': 'Nov2025', 'component': 'villages_by_blocks', 'snapshots': 1},
            {'month': 'Sep2026', 'component': 'states', 'snapshots': 1},
            {'month': 'Sep2026', 'component': 'villages', 'snapshots': 2},
        ])

    def test_filters_and_repeat_discovery_only_include_remaining_sources(self):
        selected = dict(today=self.TODAY, month='2026-09', component='villages')
        self.assertEqual(build_plan(self.FILES, **selected), [
            {'month': 'Sep2026', 'component': 'villages', 'snapshots': 2}])
        remaining = [name for name in self.FILES if not name.startswith('villages.')]
        self.assertEqual(build_plan(remaining, **selected), [])
        self.assertEqual(build_plan(['villages.01Sep2026.csv.7z'] * 2, **selected)[0]['snapshots'], 1)

    def test_invalid_or_incomplete_months_are_rejected(self):
        for month in ('2026-10', '2026-11', 'Sep2026', '2026-9', '2026-13', '../2026-09'):
            with self.subTest(month=month), self.assertRaises(ValueError):
                build_plan([], today=self.TODAY, month=month)
        with self.assertRaises(ValueError):
            build_plan([], today=self.TODAY, component='villages; false')
        with self.assertRaises(ValueError):
            build_plan(['villages.31Feb2026.csv.7z'], today=self.TODAY)

    def test_matrix_size_limit_requires_narrowing_without_silently_dropping_work(self):
        with self.assertRaisesRegex(ValueError, '256'):
            build_plan([f'dataset_{index}.01Jan2026.csv.7z' for index in range(257)], today=self.TODAY)

    def test_plan_outputs_skip_empty_matrix_and_report_work_without_mutation(self):
        for jobs in ([], build_plan(self.FILES, today=self.TODAY)):
            with self.subTest(empty=not jobs), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                with patch.dict(os.environ, GITHUB_OUTPUT=str(root / 'outputs'),
                                GITHUB_STEP_SUMMARY=str(root / 'summary')), contextlib.redirect_stdout(io.StringIO()):
                    publish_plan(jobs, root / 'plan.json')
                values = dict(line.split('=', 1) for line in (root / 'outputs').read_text().splitlines())
                self.assertEqual(values['has_work'], str(bool(jobs)).lower())
                self.assertEqual(json.loads(values['matrix']), {'include': jobs})
                self.assertEqual(json.loads((root / 'plan.json').read_text()), {'include': jobs})
                self.assertIn(f'Found {len(jobs)} pending monthly archives', (root / 'summary').read_text())


if __name__ == '__main__':
    unittest.main()
