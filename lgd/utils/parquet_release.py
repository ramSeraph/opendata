"""GitHub release storage for the standalone Parquet publishing workflow."""

import json
import re
import tempfile
from pathlib import Path

from .workflow_common import GitHub as BaseGitHub, digest, require_uploaded


RELEASE = 'lgd-parquet-latest'
RELEASE_PATTERN = re.compile(r'lgd-parquet-(latest|extra-[0-9]{4})')
MAX_ASSET_BYTES = 2 * 1024**3


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n').encode()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    try:
        temporary.write_bytes(encoded(value))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def asset_ref(repo, tag, path):
    path = Path(path)
    if not 0 < path.stat().st_size < MAX_ASSET_BYTES:
        raise ValueError(f'Empty or oversized release asset: {path.name}')
    return dict(url=f'https://github.com/{repo}/releases/download/{tag}/{path.name}',
                size=path.stat().st_size, sha256=digest(path))


def location(repo, ref):
    prefix = f'https://github.com/{repo}/releases/download/'
    if not ref['url'].startswith(prefix):
        raise ValueError('Reference belongs to another repository')
    parts = ref['url'][len(prefix):].split('/')
    if (len(parts) != 2 or not RELEASE_PATTERN.fullmatch(parts[0]) or
            not re.fullmatch(r'[A-Za-z0-9_.-]+', parts[1]) or parts[1] in ('.', '..')):
        raise ValueError('Invalid published asset URL')
    if (not isinstance(ref['size'], int) or not 0 < ref['size'] < MAX_ASSET_BYTES or
            not re.fullmatch('[a-f0-9]{64}', ref['sha256'])):
        raise ValueError('Invalid published asset size/checksum')
    return parts


class GitHub(BaseGitHub):
    def __init__(self, repository=None):
        if repository is None:
            super().__init__()
        else:
            self.repo, self.root = repository, f'repos/{repository}'
        self.refresh()

    def refresh(self):
        self.listed = {r['tag_name']: r for r in self.api('releases?per_page=100', paginate=True)}
        self.inventory = {}

    def release_assets(self, tag, *, refresh=False):
        release = self.listed.get(tag)
        if release is None:
            return {}
        if refresh or tag not in self.inventory:
            self.inventory[tag] = {a['name']: a for a in self.assets(release['id'])}
        return self.inventory[tag]

    def read_json(self, asset):
        if asset['size'] > 8 * 1024**2:
            raise ValueError('Unexpectedly large publication metadata')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'metadata.json'
            self.download(asset, path)
            return json.loads(path.read_bytes())

    def read_index(self):
        assets = self.release_assets(RELEASE, refresh=True)
        if 'metadata.json' in assets:
            return self.read_json(assets['metadata.json'])
        if any(name.startswith('metadata.') for name in assets):
            raise ValueError('Discovery metadata is missing; run publication recovery')
        return None

    def verify_ref(self, ref):
        tag, name = location(self.repo, ref)
        asset = self.release_assets(tag).get(name)
        require_uploaded(asset)
        if asset['size'] != ref['size']:
            raise ValueError(f'Published asset size differs: {name}')
        if asset.get('digest'):
            if asset['digest'] != 'sha256:' + ref['sha256']:
                raise ValueError(f'Published asset checksum differs: {name}')
        else:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/name
                self.download(asset, path)
                if digest(path) != ref['sha256']:
                    raise ValueError(f'Published asset checksum differs: {name}')
        return asset

    def ensure_release(self, tag, commit):
        if not RELEASE_PATTERN.fullmatch(tag):
            raise ValueError('Unexpected publication release tag')
        if tag not in self.listed:
            try:
                self.api('releases', '--method', 'POST', body=dict(
                    tag_name=tag, target_commitish=commit, name=tag, make_latest='false',
                    body='LGD Parquet exports. Start with metadata.json in lgd-parquet-latest.'))
            except Exception:
                # Other matrix workers may create the same reserved release.
                self.refresh()
                if tag not in self.listed:
                    raise
            self.refresh()
        release = self.listed[tag]
        if release.get('draft') or release.get('immutable'):
            raise ValueError('Publication release must be public and accept new assets')

    def put(self, tag, path, commit, *, mutable=False):
        path = Path(path)
        ref = asset_ref(self.repo, tag, path)
        if mutable and (tag != RELEASE or path.name not in ('metadata.json', 'metadata.previous.json')):
            raise ValueError('Only discovery metadata may be replaced')
        self.ensure_release(tag, commit)
        existing = self.release_assets(tag, refresh=True).get(path.name)
        if existing and existing['state'] != 'uploaded':
            self.api(f'releases/assets/{existing["id"]}', '--method', 'DELETE')
            existing = None
        if existing and not mutable:
            self.verify_ref(ref)
            return ref
        if not existing and len(self.release_assets(tag, refresh=True)) >= 1000:
            raise ValueError(f'Release asset capacity exhausted: {tag}')
        self.upload(tag, path, replace=mutable)
        self.inventory.pop(tag, None)
        self.verify_ref(ref)
        return ref
