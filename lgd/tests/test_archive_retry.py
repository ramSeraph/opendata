import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which('jq'), 'jq is required to exercise the GitHub API filters')
class ArchiveRetryTests(unittest.TestCase):
    def decide(self, conclusion, *, attempt=1, enabled=True, jobs=(), annotations=(), fail_api=False):
        workflow = Path(__file__).resolve().parents[2] / '.github/workflows/common-rerun-trigger.yml'
        step = workflow.read_text().split('      - name: Check to give up\n', 1)[1].split('      - name:', 1)[0]
        script = textwrap.dedent(step.split('        run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gh = root / 'gh'
            gh.write_text('''#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
args = sys.argv[1:]
assert '--paginate' in args
endpoint = args[args.index('--paginate') + 1]
with Path(os.environ['CALLS']).open('a') as f:
    f.write(endpoint + '\\n')
if os.environ['FAIL_API'] == 'true':
    sys.exit(1)
if '/jobs?' in endpoint:
    data = os.environ['JOBS']
else:
    data = os.environ['ANNOTATIONS']
result = subprocess.run(['jq', '-r', args[args.index('--jq') + 1]], input=data, text=True)
sys.exit(result.returncode)
''')
            gh.chmod(0o755)
            output = root / 'output'
            calls = root / 'calls'
            env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                       GITHUB_OUTPUT=str(output), GITHUB_REPOSITORY='owner/repo',
                       RUN_ID='123', RUN_NO='10', RUN_ATTEMPT=str(attempt), CONCLUSION=conclusion,
                       NUM_ATTEMPTS='2', RETRY_TIMEOUTS=str(enabled).lower(),
                       JOBS=json.dumps({'jobs': list(jobs)}), ANNOTATIONS=json.dumps(list(annotations)),
                       FAIL_API=str(fail_api).lower(), CALLS=str(calls))
            result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script],
                                    cwd=root, env=env, capture_output=True, text=True)
            values = dict(line.split('=', 1) for line in output.read_text().splitlines()) if output.exists() else {}
            return result, values, calls.read_text().splitlines() if calls.exists() else []

    def test_failure_and_timeout_obey_attempt_limit(self):
        for conclusion in ('failure', 'timed_out'):
            for attempt in (1, 2, 3):
                with self.subTest(conclusion=conclusion, attempt=attempt):
                    result, values, calls = self.decide(conclusion, attempt=attempt)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(values, {'RERUN': str(attempt < 2).lower(), 'SEND_ALERT': str(attempt >= 2).lower()})
                    self.assertEqual(calls, [])

    def test_cancelled_timeout_uses_current_attempt_and_explicit_failure_annotation(self):
        for message in ('The job has exceeded the maximum execution time of 6h0m0s',
                        'The job running on runner Hosted Agent has exceeded the maximum execution time of 240 minutes.',
                        "The action 'Compress data' has timed out after 240 minutes."):
            with self.subTest(message=message):
                result, values, calls = self.decide('cancelled', jobs=[
                    {'conclusion': 'success', 'check_run_url': 'https://api.github.com/check-runs/old'},
                    {'conclusion': 'cancelled', 'check_run_url': 'https://api.github.com/check-runs/456'}],
                    annotations=[{'annotation_level': 'failure', 'message': message}])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values, {'RERUN': 'true', 'SEND_ALERT': 'false'})
                self.assertEqual(calls, ['repos/owner/repo/actions/runs/123/attempts/1/jobs?per_page=100',
                                         'https://api.github.com/check-runs/456/annotations?per_page=100'])

    def test_manual_cancellation_and_timeout_opt_out_are_not_retried(self):
        cases = [dict(), dict(annotations=[{'annotation_level': 'failure', 'message': 'The operation was canceled.'}]),
                 dict(annotations=[{'annotation_level': 'warning', 'message': 'The job has exceeded the maximum execution time of 4h0m0s'}])]
        for case in cases:
            result, values, _ = self.decide('cancelled', attempt=2,
                jobs=[{'conclusion': 'cancelled', 'check_run_url': 'https://api.github.com/check-runs/456'}], **case)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(values, {'RERUN': 'false', 'SEND_ALERT': 'false'})
        for conclusion in ('cancelled', 'timed_out', 'success', 'skipped'):
            result, values, calls = self.decide(conclusion, enabled=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(values, {'RERUN': 'false', 'SEND_ALERT': 'false'})
            self.assertEqual(calls, [])

    def test_timed_out_job_and_failed_metadata_lookup(self):
        result, values, calls = self.decide('cancelled', jobs=[{'conclusion': 'timed_out'}])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values, {'RERUN': 'true', 'SEND_ALERT': 'false'})
        self.assertEqual(len(calls), 1)
        result, values, _ = self.decide('cancelled', fail_api=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(values, {})

    def test_retry_api_selects_failed_jobs_only_for_catchup(self):
        workflow = Path(__file__).resolve().parents[2] / '.github/workflows/common-rerun-trigger.yml'
        step = workflow.read_text().split('      - name: Call Rerun API\n', 1)[1].split('  Alert-Sender:', 1)[0]
        script = textwrap.dedent(step.split('        run: |\n', 1)[1])
        for failed_only in (False, True):
            with self.subTest(failed_only=failed_only), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                curl = root / 'curl'
                curl.write_text('#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
                curl.chmod(0o755)
                env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                           RERUN_URL='https://api.github.com/repos/owner/repo/actions/runs/123/rerun',
                           FAILED_JOBS_ONLY=str(failed_only).lower(), RERUN_USER='owner', RERUN_TOKEN='fake-token')
                result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = json.loads(result.stdout)
                self.assertIn('--fail-with-body', args)
                expected = env['RERUN_URL'] + ('-failed-jobs' if failed_only else '')
                self.assertEqual(args[-1], expected)


if __name__ == '__main__':
    unittest.main()
