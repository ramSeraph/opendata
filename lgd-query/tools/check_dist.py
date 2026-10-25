"""Check the standalone distribution boundary and its release tag before upload."""

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import zipfile
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen


def check(directory, tag=''):
    directory = Path(directory)
    wheels, sources = list(directory.glob('*.whl')), list(directory.glob('*.tar.gz'))
    # uv creates a .gitignore alongside the two build artifacts.
    artifacts = [p for p in directory.iterdir() if p.name != '.gitignore']
    if len(wheels) != 1 or len(sources) != 1 or len(artifacts) != 2:
        raise ValueError('Expected exactly one wheel and one source distribution')
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = wheel.namelist()
        metadata_names = [name for name in names if name.endswith('.dist-info/METADATA')]
        if len(metadata_names) != 1:
            raise ValueError('Missing/ambiguous wheel metadata')
        metadata = BytesParser().parsebytes(wheel.read(metadata_names[0]))
        version = metadata['Version']
        if metadata['Name'] != 'lgd-query' or not version:
            raise ValueError('Distribution belongs to another project')
        if tag and tag != f'lgd-query-v{version}':
            raise ValueError(f'Tag {tag!r} does not match package version {version}')
        prefix = f'lgd_query-{version}.dist-info/'
        if any(not name.startswith(('lgd_query/', prefix)) for name in names):
            raise ValueError('Wheel contains code outside lgd_query')
        if 'lgd_query/__init__.py' not in names or 'lgd_query/cli.py' not in names:
            raise ValueError('Reader API/CLI is missing from wheel')
        for name in names:
            if (name.startswith('lgd_query/queries/') and name.endswith('.py')
                    and not PurePosixPath(name).name.startswith('_')):
                if name[:-3] + '.pyi' not in names:
                    raise ValueError(f'Query type stub is missing from wheel: {name}')
        entry_points = wheel.read(prefix+'entry_points.txt').decode()
        if 'lgd-query = lgd_query.cli:main' not in entry_points:
            raise ValueError('CLI entry point is missing')
        if any('; extra ==' not in dep for dep in metadata.get_all('Requires-Dist', [])):
            raise ValueError('Base reader unexpectedly requires third-party dependencies')
    root = f'lgd_query-{version}'
    with tarfile.open(sources[0]) as source:
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or path.parts[0] != root or member.issym() or member.islnk():
                raise ValueError('Unexpected source distribution path/link')
            if not member.isfile():
                continue
            relative = str(path.relative_to(root))
            if relative not in ('README.md', 'pyproject.toml', 'PKG-INFO', 'setup.cfg',
                                'MANIFEST.in', 'tools/check_dist.py', 'tools/generate_query_stubs.py') and not relative.startswith(
                    ('src/lgd_query/', 'src/lgd_query.egg-info/', 'tests/')):
                raise ValueError(f'Source distribution includes unrelated files: {relative}')
    print(f'lgd-query {version}: standalone wheel and source archive verified')
    return version


def check_published(directory, version, *, require_complete=False):
    """Permit retries only when already-published PyPI files have identical bytes.

    Before uploading, a missing/partial release is allowed. Before advertising
    the files on GitHub, both distributions must match the published PyPI hashes.
    Network errors and unexpected filenames fail closed.
    """
    directory = Path(directory)
    expected = {p.name: dict(size=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for pattern in ('*.whl', '*.tar.gz') for p in directory.glob(pattern)}
    if len(expected) != 2:
        raise ValueError('Expected the two checked distributions')
    url = f'https://pypi.org/pypi/lgd-query/{quote(version, safe="")}/json'
    try:
        with urlopen(url, timeout=30) as response:
            metadata = json.load(response)
    except HTTPError as error:
        error.close()
        if error.code != 404:
            raise
        if require_complete:
            raise ValueError('Version is not yet visible on PyPI; retry after publication') from error
        return 0
    files = metadata.get('urls')
    if not isinstance(files, list):
        raise ValueError('Unrecognized PyPI release metadata')
    seen = set()
    for file in files:
        name = file['filename']
        if name not in expected or name in seen:
            raise ValueError(f'Unexpected/duplicate PyPI distribution: {name}')
        actual = dict(size=file['size'], sha256=file['digests']['sha256'])
        if actual != expected[name]:
            raise ValueError(f'PyPI already has different bytes for {name}; use the original '
                             'workflow artifacts or publish a new version')
        seen.add(name)
    if require_complete and seen != expected.keys():
        raise ValueError('Not all checked distributions are visible on PyPI; retry after publication')
    print(f'PyPI: {len(seen)} existing distributions match the checked artifacts')
    return len(seen)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', default='dist')
    parser.add_argument('--tag', default='')
    parser.add_argument('--check-pypi', action='store_true')
    parser.add_argument('--require-published', action='store_true')
    args = parser.parse_args()
    version = check(args.directory, args.tag)
    if args.check_pypi or args.require_published:
        check_published(args.directory, version, require_complete=args.require_published)
