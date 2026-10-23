"""Shared GitHub job I/O and bounded subprocess handling, independent of scraping."""

import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


WORK_SECONDS = 210 * 60


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def output(name, value):
    if not isinstance(value, str):
        value = json.dumps(value, separators=(',', ':'))
    if '\n' in value:
        raise ValueError('Job outputs must fit on one line')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as target:
        target.write(f'{name}={value}\n')


class GitHub:
    def __init__(self):
        self.repo = os.environ['GITHUB_REPOSITORY']
        self.root = f'repos/{self.repo}'

    def api(self, endpoint, *args, paginate=False, body=None):
        command = ['gh', 'api', f'{self.root}/{endpoint}', *args]
        kwargs = {}
        if body is not None:
            command.extend(['--input', '-'])
            kwargs['input'] = json.dumps(body)
        if paginate:
            command.extend(['--paginate', '--slurp'])
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=300, **kwargs)
        data = json.loads(result.stdout) if result.stdout else None
        return [item for page in data for item in page] if paginate else data

    def assets(self, release_id):
        return self.api(f'releases/{int(release_id)}/assets?per_page=100', paginate=True)

    def find_asset(self, release_id, name):
        matches = [asset for asset in self.assets(release_id) if asset['name'] == name]
        if len(matches) > 1:
            raise ValueError(f'Duplicate release asset: {name}')
        return matches[0] if matches else None

    def download(self, asset, destination):
        require_uploaded(asset)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + '.download')
        try:
            with temporary.open('wb') as target:
                subprocess.run(['gh', 'api', f'{self.root}/releases/assets/{int(asset["id"])}',
                                '-H', 'Accept: application/octet-stream'],
                               stdout=target, stderr=subprocess.PIPE, check=True, timeout=600)
            verify_download(temporary, asset)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)

    def upload(self, tag, path, *, replace=False):
        command = ['gh', 'release', 'upload', tag, str(path), '--repo', self.repo]
        if replace:
            command.append('--clobber')
        subprocess.run(command, check=True, timeout=600)


def require_uploaded(asset):
    if not asset or asset.get('state') != 'uploaded' or asset.get('size', 0) <= 0:
        raise ValueError('Release asset is missing or its upload is incomplete')


def verify_download(path, asset):
    require_uploaded(asset)
    if Path(path).stat().st_size != asset['size']:
        raise ValueError(f'Incorrect download size: {asset["name"]}')
    if asset.get('digest') and asset['digest'] != f'sha256:{digest(path)}':
        raise ValueError(f'Incorrect download checksum: {asset["name"]}')


def run_bounded(command, seconds=WORK_SECONDS):
    """Stop the entire worker process group before cache compression begins."""
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Component job was stopped')

    process = subprocess.Popen(command, start_new_session=True)
    previous_handler = signal.signal(signal.SIGTERM, interrupted)
    try:
        try:
            return process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            print('Work deadline reached; preserving completed checkpoints.', flush=True)
            return 124
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                # The parent may exit before its workers. Kill the group as well.
                time.sleep(1)
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        finally:
            signal.signal(signal.SIGTERM, previous_handler)
