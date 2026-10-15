import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class HistoryRestoreTests(unittest.TestCase):
    def restore(self, published=(), cached=(), failure=''):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        data = root / 'lgd/data/raw/transactions'
        data.mkdir(parents=True)
        (root / 'bin').mkdir()
        for filename in cached:
            (data / filename).write_text('cached data\n')

        gh = root / 'bin/gh'
        gh.write_text('''#!/bin/bash
if [[ "$RESTORE_FAILURE" == api ]]; then exit 7; fi
if [[ "$RESTORE_FAILURE" == unexpected_call ]]; then exit 9; fi
if [[ "$1 $2" == "release view" ]]; then
  printf '%s\n' "$PUBLISHED_ASSETS"
elif [[ "$5" == transactions.csv.7z ]]; then
  touch transactions.csv.7z
elif [[ "$5" == transactions_dates_covered.txt ]]; then
  if [[ "$RESTORE_FAILURE" == coverage_download ]]; then exit 8; fi
  echo 2026-10-15 > "$7"
else
  exit 10
fi
''')
        seven = root / 'bin/7z'
        seven.write_text('#!/bin/bash\necho "Transaction ID,Operation Code" > transactions.csv\n')
        for stub in (gh, seven):
            stub.chmod(0o755)

        workflow = Path(__file__).resolve().parents[2] / '.github/workflows/lgd_run.yml'
        step = workflow.read_text().split('      - name: Download transaction history from github\n', 1)[1]
        step = step.split('      - name:', 1)[0]
        script = textwrap.dedent(step.split('        run: |\n', 1)[1])
        result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], cwd=root,
                                env=dict(os.environ, PATH=f'{root / "bin"}:{os.environ["PATH"]}',
                                         PUBLISHED_ASSETS='\n'.join(published), RESTORE_FAILURE=failure),
                                capture_output=True, text=True)
        return result, data

    def test_first_run_and_complete_or_partial_published_history(self):
        for published in ((), ('transactions.csv.7z',), ('transactions_dates_covered.txt',),
                          ('transactions.csv.7z', 'transactions_dates_covered.txt')):
            with self.subTest(published=published):
                result, data = self.restore(published=published)
                self.assertEqual(result.returncode, 0, result.stderr)
                if 'transactions.csv.7z' in published:
                    self.assertTrue((data / 'combined.csv').read_text().startswith('Transaction ID,'))
                    expected = '2026-10-15\n' if 'transactions_dates_covered.txt' in published else ''
                    self.assertEqual((data / 'dates_covered.txt').read_text(), expected)
                else:
                    self.assertFalse((data / 'combined.csv').exists())
                    self.assertFalse((data / 'dates_covered.txt').exists())

    def test_cache_is_reused_but_orphan_coverage_is_discarded(self):
        result, data = self.restore(cached=('combined.csv', 'dates_covered.txt'), failure='unexpected_call')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((data / 'combined.csv').read_text(), 'cached data\n')
        for cached in (('combined.csv',), ('dates_covered.txt',)):
            with self.subTest(cached=cached):
                result, data = self.restore(cached=cached)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((data / 'dates_covered.txt').exists())
                self.assertEqual((data / 'combined.csv').exists(), 'combined.csv' in cached)

    def test_release_failures_propagate_without_marking_dates_covered(self):
        for failure in ('api', 'coverage_download'):
            with self.subTest(failure=failure):
                result, data = self.restore(
                    published=('transactions.csv.7z', 'transactions_dates_covered.txt'),
                    cached=('dates_covered.txt',), failure=failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((data / 'dates_covered.txt').exists())


if __name__ == '__main__':
    unittest.main()
