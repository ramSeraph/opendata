import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class MonitorWorkflowTests(unittest.TestCase):
    def test_monitor_reports_the_generated_file_and_propagates_failures(self):
        workflow = Path(__file__).resolve().parents[2] / '.github/workflows/lgd_monitor_site.yml'
        step = workflow.read_text().split('      - name: Monitor site for changes\n', 1)[1]
        script = textwrap.dedent(step.split('        run: |\n', 1)[1].split('        timeout-minutes:', 1)[0])
        script = script.replace('${{ steps.date.outputs.date }}', '16Oct2026')
        for outcome in ('changes', 'none', 'failure'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'lgd').mkdir()
                (root / 'bin').mkdir()
                uv = root / 'bin/uv'
                uv.write_text('''#!/bin/bash
test "${PWD##*/}" = lgd || exit 2
if [[ "$MONITOR_OUTCOME" == failure ]]; then exit 1; fi
if [[ "$MONITOR_OUTCOME" == changes ]]; then
  mkdir -p data/raw/16Oct2026
  echo '{"added":[["New dataset"]],"removed":[]}' > data/raw/16Oct2026/struct_changes.json
fi
''')
                uv.chmod(0o755)
                output = root / 'output'
                env = dict(os.environ, PATH=f'{root / "bin"}:{os.environ["PATH"]}',
                           GITHUB_OUTPUT=str(output), MONITOR_OUTCOME=outcome)
                result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script],
                                        cwd=root, env=env, capture_output=True, text=True)
                if outcome == 'failure':
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    expected = 'none' if outcome == 'none' else 'lgd/data/raw/16Oct2026/struct_changes.json'
                    self.assertEqual(output.read_text().strip(), f'changes={expected}')
                    if outcome == 'changes':
                        self.assertTrue((root / expected).is_file())


if __name__ == '__main__':
    unittest.main()
