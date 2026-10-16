import hashlib
import json
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

def run_external(cmd):
    print(f'running cmd - {cmd}')
    start = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    print(f'STDOUT: {res.stdout}')
    print(f'STDERR: {res.stderr}')
    print(f'command took {end - start} secs to run')
    if res.returncode != 0:
        raise Exception(f'command {cmd} failed with exit code: {res.returncode}')

def get_all_releases():
    run_external('sh -c "gh release list --limit 100 --json tagName > tags.json"')
    tfile = Path('tags.json')
    data = json.loads(tfile.read_text())
    tfile.unlink()
    releases = [ r['tagName'] for r in data ]
    return releases

def get_all_archive_names(releases):
    fnames = {}
    for release in releases:
        run_external(f'sh -c "gh release view {release} --json assets > release.json"')
        rfile = Path('release.json')
        data = json.loads(rfile.read_text())
        rfile.unlink()
        assets = data['assets']
        fnames.update({ a['name']:release for a in assets })

    return fnames

def get_mapping(names):
    m = {}
    for name in names:
        parts = name.split('.')
        prefix = parts[0]
        date = parts[1]
        if prefix not in m:
            m[prefix] = []
        m[prefix].append(date)
    return m

def filter_releases(releases, prefix):
    filtered = []
    for r in releases:
        if r == prefix:
            filtered.append(r)
            continue
        if r.startswith(prefix + '-'):
            filtered.append(r)
    return filtered


def get_release_asset(release, name):
    result = subprocess.run(['gh', 'release', 'view', release, '--json', 'assets'],
                            check=True, capture_output=True, text=True)
    assets = [asset for asset in json.loads(result.stdout)['assets'] if asset['name'] == name]
    if len(assets) > 1:
        raise ValueError(f'Multiple assets named {name} in {release}')
    return assets[0] if assets else None


def require_uploaded(asset, name):
    if not asset or asset.get('state') != 'uploaded' or asset.get('size', 0) <= 0:
        raise ValueError(f'{name} is not a completed release upload')


def file_digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def check_download_metadata(path, asset):
    require_uploaded(asset, path.name)
    if path.stat().st_size != asset['size']:
        raise ValueError(f'{path} does not match the published size')
    digest = asset.get('digest')
    if digest:
        if digest != f'sha256:{file_digest(path)}':
            raise ValueError(f'{path} does not match the published SHA-256')
        return True
    return False


def download_asset(path, release, name):
    run_external(shlex.join(['gh', 'release', 'download', release, '-p', name,
                             '-O', str(path), '--clobber']))


def verify_published_file(path, release):
    # Always inspect the remote asset, even when the local archive came from cache.
    asset = get_release_asset(release, path.name)
    if check_download_metadata(path, asset):
        return
    # Older assets may lack GitHub's SHA-256. Compare the actual published bytes.
    temporary = path.with_suffix(path.suffix + '.verify.tmp')
    try:
        download_asset(temporary, release, path.name)
        check_download_metadata(temporary, asset)
        if file_digest(temporary) != file_digest(path):
            raise ValueError(f'{path} differs from the published file')
    finally:
        temporary.unlink(missing_ok=True)


def remove_empty_upload(release, name):
    asset = get_release_asset(release, name)
    if asset and asset.get('state') == 'starter' and asset.get('size') == 0:
        # GitHub can leave this placeholder after a failed upload. Delete by ID
        # so a replacement asset with the same name can never be removed here.
        print(f'removing empty upload placeholder {name} from {release}')
        run_external(shlex.join(['gh', 'api', '--method', 'DELETE', asset['apiUrl']]))
        return True
    require_uploaded(asset, name)
    return False


def validate_archive_files(archive, file_names, allow_extra=False):
    result = subprocess.run(['7z', 'l', '-slt', '-ba', str(archive)],
                            check=True, capture_output=True, text=True)
    names = [line.removeprefix('Path = ') for line in result.stdout.splitlines()
             if line.startswith('Path = ')]
    expected = set(file_names)
    actual = set(names)
    if len(names) != len(actual) or expected - actual or (not allow_extra and actual - expected):
        raise ValueError(f'{archive} has unexpected contents: missing={sorted(expected - actual)}, '
                         f'extra={sorted(actual - expected)}')


def test_archive_integrity(archive):
    subprocess.run(['7z', 't', str(archive)], check=True, capture_output=True, text=True)


def extract_daily_archive(archive, destination):
    validate_archive_files(archive, [destination.name])
    temporary = destination.with_suffix(destination.suffix + '.tmp')
    try:
        with temporary.open('wb') as output:
            subprocess.run(['7z', 'e', '-so', str(archive), destination.name],
                           stdout=output, stderr=subprocess.PIPE, check=True)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def compress_archive(archive, files, zipping_dir):
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_suffix(archive.suffix + '.tmp')
    temporary.unlink(missing_ok=True)
    try:
        command = ['7z', 'a', '-t7z', '-mmt=off', '-m0=lzma2', '-mx=9',
                   '-ms=on', '-md=1G', '-mfb=273', str(temporary.resolve())]
        command.extend(file.name for file in files)
        run_external(f'cd {shlex.quote(str(zipping_dir))} && {shlex.join(command)}')
        validate_archive_files(temporary, [file.name for file in files])
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)


def download_published_archive(archive, release, file_names):
    asset = get_release_asset(release, archive.name)
    require_uploaded(asset, archive.name)
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_suffix(archive.suffix + '.tmp')
    try:
        download_asset(temporary, release, archive.name)
        check_download_metadata(temporary, asset)
        # A retry may have already deleted some of the daily source files.
        validate_archive_files(temporary, file_names, allow_extra=True)
        test_archive_integrity(temporary)
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)


def refresh_indexes():
    for release in ('lgd-archive', 'lgd-latest'):
        run_external(f"uvx --from gh-release-tools generate-lists -r '{release}' -e '.7z'")

def upload_to_archive(fname, counts, archive_releases):
    monthly_archive_name = Path(fname).name

    def sort_key(r_name):
        if r_name == 'lgd-archive':
            return -1
        match = re.search(r'extra(\d+)', r_name)
        if match:
            return int(match.group(1))
        return float('inf')

    sorted_releases = sorted(list(archive_releases), key=sort_key)

    for k in sorted_releases:
        max_count = 988 if k == 'lgd-archive' else 998
        if counts.get(k, 0) >= max_count:
            continue
        print(f'uploading {monthly_archive_name} to {k}')
        run_external(f'gh release upload {k} data/combined/{monthly_archive_name}')
        counts[k] = counts.get(k, 0) + 1
        return k

    max_num = 0
    for r in archive_releases:
        match = re.search(r'extra(\d+)', r)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num

    new_release_name = f'lgd-archive-extra{max_num + 1}'
    print(f'No archive available for {monthly_archive_name}, creating new release {new_release_name}')

    notes = "Extension of [lgd-archive](https://github.com/ramSeraph/opendata/releases/tag/lgd-archive)\n\n"
    notes += "Files and their sizes are listed at [listing_files.csv](https://github.com/ramSeraph/opendata/releases/download/lgd-archive/listing_files.csv)\n"

    title = f"Local Government Directory monthly archives Supplementary{max_num + 1}"

    run_external(shlex.join(['gh', 'release', 'create', new_release_name,
                             '--notes', notes, '--title', title]))

    print(f'uploading {monthly_archive_name} to {new_release_name}')
    run_external(f'gh release upload {new_release_name} data/combined/{monthly_archive_name}')
    counts[new_release_name] = 1
    archive_releases.append(new_release_name)
    return new_release_name

def redistribute_latest(latest_releases):
    all_archives_mapping = get_all_archive_names(latest_releases)
    by_release = {}
    for name, release in all_archives_mapping.items():
        if release not in by_release:
            by_release[release] = []
        by_release[release].append(name)

    def sort_key(r_name):
        if r_name == 'lgd-latest':
            return 0
        match = re.search(r'extra(\d+)', r_name)
        if match:
            return int(match.group(1))
        # Should not happen given the filtering, but as a fallback
        return float('inf')

    release_names = sorted(list(by_release.keys()), key=sort_key)

    slots = {}
    for release in release_names:
        max_count = 988 if release == 'lgd-latest' else 998
        slots[release] = max_count - len(by_release.get(release, []))

    moves = []
    # Iterate through releases from first to second-to-last
    for i in range(len(release_names)):
        target_release = release_names[i]

        # If no slots in target, we can't move anything to it.
        if slots[target_release] <= 0:
            continue

        # Iterate backwards from the last release to find files to move.
        # This helps in emptying the last releases first.
        for j in range(len(release_names) - 1, i, -1):
            source_release = release_names[j]

            files_in_source = by_release.get(source_release, [])
            if not files_in_source:
                continue

            # Determine how many files to move
            num_to_move = min(slots[target_release], len(files_in_source))

            if num_to_move <= 0:
                continue

            # Get the actual files to move (we can just take the first `num_to_move` items)
            files_to_relocate = files_in_source[:num_to_move]

            for fname in files_to_relocate:
                moves.append((fname, source_release, target_release))

            # Update our in-memory state to reflect the planned move
            # 1. Remove files from source
            by_release[source_release] = files_in_source[num_to_move:]
            # 2. Add files to target
            if target_release not in by_release:
                by_release[target_release] = []
            by_release[target_release].extend(files_to_relocate)
            # 3. Update slot counts
            slots[source_release] += num_to_move
            slots[target_release] -= num_to_move

    if not moves:
        print("No redistribution of assets is needed.")
        return

    print(f"Found {len(moves)} assets to redistribute.")

    redistribute_dir = Path('redistribute_temp')
    redistribute_dir.mkdir(exist_ok=True, parents=True)

    for fname, source, target in moves:
        local_path = redistribute_dir / fname
        print(f"Preparing to move {fname} from {source} to {target}")
        run_external(f'gh release download {source} -p "{fname}" -D "{redistribute_dir}"')
        run_external(f'gh release upload {target} "{local_path}"')
        run_external(f'gh release delete-asset {source} "{fname}" -y')
        local_path.unlink()

    shutil.rmtree(redistribute_dir, ignore_errors=True)


def update_mapping(prefix, dates):
    release = 'lgd-archive'
    destination = Path('archive_mapping.json')
    backup = Path('archive_mapping.backup.json')
    asset = get_release_asset(release, destination.name)
    recovering = asset is None or (asset.get('state') == 'starter' and asset.get('size') == 0)
    source_name = backup.name if recovering else destination.name
    if recovering:
        print('recovering mapping from the backup after an interrupted replacement')
        asset = get_release_asset(release, backup.name)
    require_uploaded(asset, source_name)
    try:
        download_asset(destination, release, source_name)
        check_download_metadata(destination, asset)
        mapping = json.loads(destination.read_text())
        if not isinstance(mapping, dict) or any(not isinstance(values, list) for values in mapping.values()):
            raise ValueError('Invalid archive mapping')

        # --clobber deletes the old asset first. Keep a verified remote copy
        # before replacing it; retries can recover even on a fresh runner.
        if not recovering:
            shutil.copyfile(destination, backup)
            run_external(f'gh release upload {release} {backup} --clobber')
            verify_published_file(backup, release)

        mapping.setdefault(prefix, []).extend(dates)
        mapping = {key: sorted(set(values)) for key, values in mapping.items()}
        destination.write_text(json.dumps(mapping))
        run_external(f'gh release upload {release} {destination} --clobber')
        verify_published_file(destination, release)
    finally:
        destination.unlink(missing_ok=True)
        backup.unlink(missing_ok=True)

def archive_month(month_year):
    releases = get_all_releases()

    archive_releases = filter_releases(releases, 'lgd-archive')
    latest_releases = filter_releases(releases, 'lgd-latest')

    all_archives_mapping = get_all_archive_names(latest_releases)
    all_archives = list(all_archives_mapping.keys())

    all_monthly_archives_mapping = get_all_archive_names(archive_releases)
    archive_counts = {}
    for k,v in all_monthly_archives_mapping.items():
        if v not in archive_counts:
            archive_counts[v] = 0
        archive_counts[v] += 1

    relevant_names = [a for a in all_archives if a.endswith(f'{month_year}.csv.7z')]

    by_file = get_mapping(relevant_names)

    zipping_dir = Path('data/zipping_area')
    zipping_dir.mkdir(exist_ok=True, parents=True)

    for prefix, dates in by_file.items():
        monthly_archive_name = f'{prefix}.{month_year}.7z'
        prefix_file = Path(f'data/combined/{monthly_archive_name}')
        asset_names = [f'{prefix}.{d}.csv.7z' for d in dates]
        to_zip = [zipping_dir / f'{prefix}.{d}.csv' for d in dates]
        file_names = [file.name for file in to_zip]
        published_release = all_monthly_archives_mapping.get(monthly_archive_name)

        if prefix_file.exists():
            try:
                validate_archive_files(prefix_file, file_names, allow_extra=bool(published_release))
                test_archive_integrity(prefix_file)
            except (subprocess.CalledProcessError, ValueError):
                print(f'discarding incomplete cached archive {prefix_file}')
                prefix_file.unlink()

        if published_release and remove_empty_upload(published_release, monthly_archive_name):
            archive_counts[published_release] -= 1
            published_release = None

        if published_release:
            # Complete mapping/deletion/index work interrupted after an upload.
            # Check the actual archive before deleting any remaining daily files.
            if prefix_file.exists():
                verify_published_file(prefix_file, published_release)
            else:
                download_published_archive(prefix_file, published_release, file_names)
        else:
            if not prefix_file.exists():
                for file, zname in zip(to_zip, asset_names):
                    # Refresh staging files from older versions as well: their
                    # extraction may have been interrupted before atomic writes.
                    zfile = zipping_dir / zname
                    rname = all_archives_mapping[zname]
                    download_asset(zfile, rname, zname)
                    extract_daily_archive(zfile, file)
                    zfile.unlink()
                compress_archive(prefix_file, to_zip, zipping_dir)

            published_release = upload_to_archive(str(prefix_file), archive_counts, archive_releases)
            verify_published_file(prefix_file, published_release)

        update_mapping(prefix, dates)

        print('deleting already archived files from latest release')
        for asset_name in asset_names:
            rname = all_archives_mapping[asset_name]
            print(f'deleting asset {asset_name} from release {rname}')
            run_external(f'gh release delete-asset {rname} {asset_name} -y')

        refresh_indexes()
        prefix_file.unlink()
        for file in to_zip:
            file.unlink(missing_ok=True)

    print('redistributing latest release assets after deletions')
    redistribute_latest(latest_releases)
    # Redistribution changes download URLs; refresh even if there was no new archive.
    refresh_indexes()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('month', help='Month to archive, e.g. Sep2026')
    args = parser.parse_args()
    archive_month(args.month)

