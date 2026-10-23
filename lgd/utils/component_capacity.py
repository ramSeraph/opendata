"""Assign ready component jobs to free GitHub concurrency groups.

Only the serialized Admit jobs may update this ledger. GitHub's per-slot
concurrency groups remain the hard execution limit. The ledger lives in an
informational check run, never in repository commits or dataset releases.
"""

import argparse
import json
import os
import re
import time

from .workflow_common import GitHub, output


CHECK_NAME = 'LGD component capacity'
POLL_SECONDS = 15
WAIT_SECONDS = 230 * 60
VISIBILITY_SECONDS = 120


def identity():
    return int(os.environ['GITHUB_RUN_ID']), int(os.environ['GITHUB_RUN_ATTEMPT'])


def validate_limit(max_jobs):
    if type(max_jobs) is not int or not 1 <= max_jobs <= 35:
        raise ValueError('LGD_MAX_COMPONENT_JOBS must be between 1 and 35')


def check_output(state):
    leases = state['leases']
    summary = f"At most {state['max_jobs']} component jobs. "
    summary += 'Reservations last observed by admission: '
    summary += ', '.join(f"slot {slot}: {lease['component']}" for slot, lease in sorted(leases.items())) or 'none'
    return dict(title=CHECK_NAME, summary=summary, text=json.dumps(state, separators=(',', ':')))


def create(github, max_jobs):
    validate_limit(max_jobs)
    run_id, attempt = identity()
    state = dict(version=1, run_id=run_id, attempt=attempt, max_jobs=max_jobs, leases={})
    check = github.api('check-runs', '--method', 'POST', body=dict(
        name=CHECK_NAME, head_sha=os.environ['GITHUB_SHA'],
        external_id=f'lgd-capacity:{run_id}:{attempt}',
        details_url=f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{github.repo}/actions/runs/{run_id}",
        status='completed', conclusion='neutral', output=check_output(state)))
    return check['id']


def read(github, check_id):
    check = github.api(f'check-runs/{check_id}')
    run_id, attempt = identity()
    if (check['name'] != CHECK_NAME or check['head_sha'] != os.environ['GITHUB_SHA']
            or check['external_id'] != f'lgd-capacity:{run_id}:{attempt}'):
        raise ValueError('Capacity reservation is from another run/attempt. Re-run all jobs.')
    state = json.loads(check['output']['text'])
    if state.get('version') != 1 or (state.get('run_id'), state.get('attempt')) != (run_id, attempt):
        raise ValueError('Invalid capacity ledger identity')
    validate_limit(state['max_jobs'])
    components = set()
    for slot, lease in state['leases'].items():
        if (slot not in {str(i) for i in range(state['max_jobs'])}
                or not re.fullmatch(r'[A-Z][A-Z0-9_]*', lease['component'])
                or type(lease['admit_job_id']) is not int or lease['admit_job_id'] <= 0
                or lease['component'] in components):
            raise ValueError('Invalid capacity reservation')
        components.add(lease['component'])
    return state


def jobs_for_attempt(github):
    run_id, attempt = identity()
    jobs, page = [], 1
    while True:
        data = github.api(f'actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page={page}')
        jobs.extend(data['jobs'])
        if len(data['jobs']) < 100:
            break
        page += 1
    return jobs


def reserve(state, jobs, component, admit_job_id):
    """Reap only proven terminal owners, then reserve any available slot."""
    by_name = {job['name']: job for job in jobs}
    by_id = {job['id']: job for job in jobs}
    if len(by_name) != len(jobs) or len(by_id) != len(jobs):
        raise ValueError('Ambiguous component jobs in workflow attempt')
    leases = state['leases']
    for slot, lease in list(leases.items()):
        worker = by_name.get(f"{lease['component']} / Component")
        admission = by_id.get(lease['admit_job_id'])
        # A reserved worker may not yet exist in the API. An absent job or a
        # successful Admit alone is never evidence that its slot is free.
        terminal = worker is not None and worker['status'] == 'completed'
        failed_admission = (worker is None and admission is not None
                            and admission['status'] == 'completed'
                            and admission['conclusion'] not in (None, 'success'))
        if terminal or failed_admission:
            del leases[slot]
    for slot, lease in leases.items():
        if lease['component'] == component:
            if lease['admit_job_id'] != admit_job_id:
                raise ValueError(f'Another admission already owns {component}')
            return int(slot)
    free = next((i for i in range(state['max_jobs']) if str(i) not in leases), None)
    if free is not None:
        leases[str(free)] = dict(component=component, admit_job_id=admit_job_id)
    return free


def acquire(github, check_id, component):
    if not re.fullmatch(r'[A-Z][A-Z0-9_]*', component):
        raise ValueError('Invalid component name')
    started = time.monotonic()
    deadline = started + WAIT_SECONDS
    while time.monotonic() < deadline:
        state = read(github, check_id)
        jobs = jobs_for_attempt(github)
        admissions = [job for job in jobs if job['name'] == f'{component} / Admit'
                      and job['status'] == 'in_progress']
        if not admissions and time.monotonic() < started + VISIBILITY_SECONDS:
            print(f'{component} waiting for its admission job to appear in GitHub', flush=True)
            time.sleep(POLL_SECONDS)
            continue
        if len(admissions) != 1:
            raise ValueError(f'Cannot identify the active admission job for {component}')
        slot = reserve(state, jobs, component, admissions[0]['id'])
        if slot is not None:
            # No worker may start until its reservation is durably recorded.
            github.api(f'check-runs/{check_id}', '--method', 'PATCH',
                       body=dict(output=check_output(state)))
            output('slot', str(slot))
            output('attempt', str(identity()[1]))
            print(f'{component} reserved free slot {slot}', flush=True)
            return
        print(f'{component} waiting: all {state["max_jobs"]} component slots are occupied', flush=True)
        time.sleep(POLL_SECONDS)
    raise TimeoutError('No component capacity became available within the admission budget')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check_id', type=int)
    parser.add_argument('component')
    args = parser.parse_args()
    acquire(GitHub(), args.check_id, args.component)


if __name__ == '__main__':
    main()
