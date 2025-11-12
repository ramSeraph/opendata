import re
import json
import time
import shutil
import subprocess
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

def filter_releases(release, prefix):
    filtered = []
    for r in releases:
        if r == prefix:
            filtered.append(r)
            continue
        if r.startswith(prefix + '-'):
            filtered.append(r)
    return filtered

def upload_to_archive(fname, counts, archive_releases):
    monthly_archive_name = Path(fname).name
    uploaded = False

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
        uploaded = True
        break

    if uploaded:
        return

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

    run_external(f'gh release create {new_release_name} --notes "{notes}" --title {title}')

    print(f'uploading {monthly_archive_name} to {new_release_name}')
    run_external(f'gh release upload {new_release_name} data/combined/{monthly_archive_name}')
    counts[new_release_name] = 1
    archive_releases.append(new_release_name)

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
    print('downloading mapping file')
    run_external('gh release download lgd-archive -p archive_mapping.json')

    print('regenerating archive mapping')
    mapping = json.loads(Path('archive_mapping.json').read_text())
    if prefix not in mapping:
        mapping[prefix] = []

    for d in dates:
        mapping[prefix].append(d)

    for prefix in mapping.keys():
        mapping[prefix] = list(set(mapping[prefix]))

    Path('archive_mapping.json').write_text(json.dumps(mapping))

    print('uploading updated mapping')
    run_external('gh release upload lgd-archive archive_mapping.json --clobber')

    Path('archive_mapping.json').unlink()





if __name__ == '__main__':
    import sys


    month_year = sys.argv[1]

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

    all_monthly_archives = set(all_monthly_archives_mapping.keys())

    relevant_names = [ a for a in all_archives if a.endswith(f'{month_year}.csv.7z') ]

    by_file = get_mapping(relevant_names)

    zipping_dir = Path('data/zipping_area')
    zipping_dir.mkdir(exist_ok=True, parents=True)

    for prefix, dates in by_file.items():
        to_zip = []

        monthly_archive_name = f'{prefix}.{month_year}.7z'
        if monthly_archive_name in all_monthly_archives:
            continue

        prefix_file = Path(f'data/combined/{monthly_archive_name}')

        asset_names = [f'{prefix}.{d}.csv.7z' for d in dates]

        for d in dates:
            zname = f'{prefix}.{d}.csv.7z'
            fname = f'{prefix}.{d}.csv'

            zfile = zipping_dir / zname
            file  = zipping_dir / fname
            if file.exists():
                continue

            print(f'downloading {zname}')
            rname = all_archives_mapping[zname]
            run_external(f'gh release download {rname} -p {zname} -D {zipping_dir}')

            print(f'extracting {zname}')
            run_external(f'sh -c "cd {zipping_dir}; 7z e {zname}"')

            print(f'deleting {zfile}')
            zfile.unlink()

            to_zip.append(file)

        to_zip_str = ' '.join([f.name for f in to_zip])

        if not prefix_file.exists():
            run_external(f'sh -c "cd {zipping_dir}; 7z a -t7z -mmt=off -m0=lzma2 -mx=9 -ms=on -md=1G -mfb=273 ../combined/{monthly_archive_name} {to_zip_str}"')

        upload_to_archive(f'data/combined/{monthly_archive_name}', archive_counts, archive_releases)

        prefix_file.unlink()

        print(f'deleting all unzipped files for {prefix}')
        for p in to_zip:
            p.unlink()

        update_mapping(prefix, dates)

        print('deleting already archived files from latest release')
        for asset_name in asset_names:
            rname = all_archives_mapping[asset_name]
            print(f'deleting asset {asset_name} from release {rname}')
            run_external(f'gh release delete-asset {rname} {asset_name} -y')

    print('redistributing latest release assets after deletions')
    redistribute_latest(latest_releases)



    

