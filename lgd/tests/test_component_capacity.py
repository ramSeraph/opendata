import copy
import json
import os
import unittest
from unittest.mock import Mock, patch

from utils import component_capacity as capacity
from utils import workflow_common


ENV = dict(GITHUB_RUN_ID='42', GITHUB_RUN_ATTEMPT='1', GITHUB_SHA='abc123',
           GITHUB_REPOSITORY='owner/repo')


def ledger(max_jobs=3):
    return dict(version=1, run_id=42, attempt=1, max_jobs=max_jobs, leases={})


def job(ident, component, kind='Component', status='in_progress', conclusion=None):
    return dict(id=ident, name=f'{component} / {kind}', status=status, conclusion=conclusion)


class CapacityTests(unittest.TestCase):
    def test_ready_component_uses_freed_slot_while_other_slots_remain_busy(self):
        state = ledger()
        state['leases'] = {
            '0': dict(component='ORG_UNIT_DETAILS', admit_job_id=10),
            '1': dict(component='STATE_ORG_DESIGNATIONS', admit_job_id=11),
            '2': dict(component='ORG_UNIT_COVERAGE', admit_job_id=12),
        }
        jobs = [job(20, 'ORG_UNIT_DETAILS'), job(21, 'STATE_ORG_DESIGNATIONS'),
                job(22, 'ORG_UNIT_COVERAGE', status='completed', conclusion='failure')]
        self.assertEqual(capacity.reserve(state, jobs, 'STATE_ORG_UNITS', 13), 2)
        self.assertEqual(state['leases']['0']['component'], 'ORG_UNIT_DETAILS')
        self.assertEqual(state['leases']['2']['component'], 'STATE_ORG_UNITS')
        self.assertIsNone(capacity.reserve(state, jobs, 'ANOTHER_COMPONENT', 14))

    def test_startup_gap_does_not_release_a_reservation(self):
        state = ledger(1)
        self.assertEqual(capacity.reserve(state, [], 'FIRST', 10), 0)
        # Admit completed, but its worker isn't visible in the API yet.
        jobs = [job(10, 'FIRST', 'Admit', 'completed', 'success')]
        self.assertIsNone(capacity.reserve(state, jobs, 'SECOND', 11))
        # Repeating the same admission cannot consume an additional slot.
        self.assertEqual(capacity.reserve(state, jobs, 'FIRST', 10), 0)
        with self.assertRaisesRegex(ValueError, 'Another admission'):
            capacity.reserve(state, jobs, 'FIRST', 12)

    def test_failed_admission_without_a_worker_releases_its_reservation(self):
        for outcome in ('failure', 'cancelled', 'timed_out'):
            with self.subTest(outcome=outcome):
                state = ledger(1)
                capacity.reserve(state, [], 'FIRST', 10)
                jobs = [job(10, 'FIRST', 'Admit', 'completed', outcome)]
                self.assertEqual(capacity.reserve(state, jobs, 'SECOND', 11), 0)

    def test_missing_or_active_workers_are_never_reaped_by_age(self):
        for jobs in [[], [job(20, 'FIRST', status='queued')],
                     [job(20, 'FIRST', status='pending')], [job(20, 'FIRST')],
                     [job(10, 'FIRST', 'Admit', 'completed', 'cancelled'), job(20, 'FIRST')]]:
            with self.subTest(jobs=jobs):
                state = ledger(1)
                capacity.reserve(state, [], 'FIRST', 10)
                self.assertIsNone(capacity.reserve(state, jobs, 'SECOND', 11))

    def test_every_terminal_worker_outcome_releases_capacity(self):
        for outcome in ('success', 'failure', 'cancelled', 'timed_out', 'skipped'):
            with self.subTest(outcome=outcome):
                state = ledger(1)
                capacity.reserve(state, [], 'FIRST', 10)
                jobs = [job(20, 'FIRST', status='completed', conclusion=outcome)]
                self.assertEqual(capacity.reserve(state, jobs, 'SECOND', 11), 0)

    def test_capacity_bound_includes_reserved_jobs_not_yet_started(self):
        for maximum in (1, 3, 5):
            state = ledger(maximum)
            for index in range(maximum):
                self.assertEqual(capacity.reserve(state, [], f'DATA_{index}', index + 1), index)
            self.assertIsNone(capacity.reserve(state, [], 'OVER_CAPACITY', 99))
            self.assertEqual(len(state['leases']), maximum)

    def test_ambiguous_job_list_fails_without_freeing_any_slot(self):
        state = ledger(1)
        capacity.reserve(state, [], 'FIRST', 10)
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            capacity.reserve(state, [job(20, 'FIRST'), job(21, 'FIRST', status='completed')], 'SECOND', 11)
        self.assertEqual(state, before)

    def test_invalid_limits_are_rejected(self):
        for maximum in (0, -1, 36, '3', True):
            with self.subTest(maximum=maximum), self.assertRaises(ValueError):
                capacity.validate_limit(maximum)


class CapacityApiTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, ENV))
        self.github = Mock(repo='owner/repo')

    def check(self, state=None):
        return dict(id=7, name=capacity.CHECK_NAME, head_sha='abc123',
                    external_id='lgd-capacity:42:1', output=capacity.check_output(state or ledger()))

    def test_create_is_informational_check_metadata_only(self):
        self.github.api.return_value = {'id': 7}
        self.assertEqual(capacity.create(self.github, 3), 7)
        call = self.github.api.call_args
        self.assertEqual(call.args, ('check-runs', '--method', 'POST'))
        body = call.kwargs['body']
        self.assertEqual(body['status'], 'completed')
        self.assertEqual(body['conclusion'], 'neutral')
        self.assertEqual(json.loads(body['output']['text']), ledger())

    def test_wrong_run_attempt_and_corrupt_ledger_are_rejected(self):
        invalid = [dict(self.check(), external_id='lgd-capacity:99:1'),
                   dict(self.check(), external_id='lgd-capacity:42:2'),
                   dict(self.check(), head_sha='other-sha'),
                   self.check(dict(ledger(), attempt=2)),
                   self.check(dict(ledger(), max_jobs=0)),
                   self.check(dict(ledger(), leases={'9': dict(component='DATA', admit_job_id=1)}))]
        for check in invalid:
            with self.subTest(check=check), self.assertRaises(ValueError):
                self.github.api.return_value = check
                capacity.read(self.github, 7)

    def test_job_lookup_is_paginated_and_specific_to_this_attempt(self):
        first = [job(i, f'DATA_{i}') for i in range(100)]
        self.github.api.side_effect = [{'jobs': first}, {'jobs': [job(101, 'LAST')]}]
        self.assertEqual(len(capacity.jobs_for_attempt(self.github)), 101)
        self.assertEqual([call.args[0] for call in self.github.api.call_args_list],
                         ['actions/runs/42/attempts/1/jobs?per_page=100&page=1',
                          'actions/runs/42/attempts/1/jobs?per_page=100&page=2'])

    def test_admission_waits_until_worker_finishes_then_persists_before_granting(self):
        state = ledger(1)
        state['leases']['0'] = dict(component='FIRST', admit_job_id=10)
        waiting = job(11, 'SECOND', 'Admit')
        self.github.api.side_effect = [
            self.check(state), {'jobs': [job(20, 'FIRST'), waiting]},
            self.check(state), {'jobs': [job(20, 'FIRST', status='completed', conclusion='success'), waiting]},
            {},
        ]
        with patch.object(capacity.time, 'sleep') as sleep, patch.object(capacity, 'output') as output:
            capacity.acquire(self.github, 7, 'SECOND')
        sleep.assert_called_once_with(capacity.POLL_SECONDS)
        saved = json.loads(self.github.api.call_args.kwargs['body']['output']['text'])
        self.assertEqual(saved['leases'], {'0': dict(component='SECOND', admit_job_id=11)})
        self.assertEqual([call.args for call in output.call_args_list], [('slot', '0'), ('attempt', '1')])

    def test_failed_ledger_write_never_grants_capacity(self):
        self.github.api.side_effect = [self.check(), {'jobs': [job(11, 'SECOND', 'Admit')]},
                                       RuntimeError('metadata write failed')]
        with patch.object(capacity, 'output') as output:
            with self.assertRaisesRegex(RuntimeError, 'metadata write failed'):
                capacity.acquire(self.github, 7, 'SECOND')
            output.assert_not_called()

    def test_new_admission_can_wait_for_job_api_visibility_without_granting_early(self):
        self.github.api.side_effect = [
            self.check(), {'jobs': []},
            self.check(), {'jobs': [job(11, 'SECOND', 'Admit')]}, {},
        ]
        with patch.object(capacity.time, 'sleep') as sleep, patch.object(capacity, 'output') as output:
            capacity.acquire(self.github, 7, 'SECOND')
        sleep.assert_called_once_with(capacity.POLL_SECONDS)
        self.assertEqual([call.args for call in output.call_args_list], [('slot', '0'), ('attempt', '1')])
        self.assertEqual(sum(call.args[-1] == 'PATCH' for call in self.github.api.call_args_list), 1)

    def test_missing_admission_stops_after_visibility_grace_without_granting(self):
        self.github.api.side_effect = [self.check(), {'jobs': []}]
        with patch.object(capacity.time, 'monotonic', side_effect=[0, 1, capacity.VISIBILITY_SECONDS]), \
                patch.object(capacity, 'output') as output:
            with self.assertRaisesRegex(ValueError, 'Cannot identify'):
                capacity.acquire(self.github, 7, 'SECOND')
        output.assert_not_called()

    def test_admission_has_bounded_wait(self):
        with patch.object(capacity.time, 'monotonic', side_effect=[0, capacity.WAIT_SECONDS]):
            with self.assertRaises(TimeoutError):
                capacity.acquire(self.github, 7, 'SECOND')
        self.github.api.assert_not_called()

    def test_api_json_uses_stdin_without_shell_interpolation(self):
        body = {'output': {'text': 'literal `value` $(value)\nnext line'}}
        with patch.object(workflow_common.subprocess, 'run', return_value=Mock(stdout='{"id":7}')) as run:
            self.assertEqual(workflow_common.GitHub().api('check-runs', '--method', 'POST', body=body), {'id': 7})
        self.assertEqual(json.loads(run.call_args.kwargs['input']), body)
        self.assertEqual(run.call_args.args[0][-2:], ['--input', '-'])


if __name__ == '__main__':
    unittest.main()
