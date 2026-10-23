"""Run pinned gh-release-tools with unbounded, namespace-filtered discovery.

gh-release-tools 0.1.14 uses `gh release list -L 500`. Override only discovery;
keep its upload placement and listing formats compatible with existing users.
"""

import importlib
import json
import re
import subprocess
import sys


def get_release_map(tag, repo=None):
    endpoint = f'repos/{repo or "{owner}/{repo}"}/releases?per_page=100'
    result = subprocess.run(['gh', 'api', '--paginate', '--slurp', endpoint],
                            check=True, capture_output=True, text=True)
    pattern = re.compile(rf'{re.escape(tag)}(?:-extra(?P<num>[0-9]+))?')
    mapping = {}
    for page in json.loads(result.stdout):
        for release in page:
            match = pattern.fullmatch(release['tag_name'])
            if match:
                number = int(match['num']) if match['num'] else 0
                if match['num'] and number == 0:
                    raise ValueError('Release cannot have -extra0 suffix')
                mapping[number] = release['tag_name']
    return mapping


def main():
    commands = {'upload-to-release': 'upload_to_release', 'generate-lists': 'generate_lists'}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        raise SystemExit('Expected upload-to-release or generate-lists')
    from release_tools import utils
    utils.get_release_map = get_release_map
    name = commands[sys.argv.pop(1)]
    return importlib.import_module('release_tools.' + name).cli()


if __name__ == '__main__':
    sys.exit(main())
