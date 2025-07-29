import re
import json
import time
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
    run_external('sh -c "gh release list --json tagName > tags.json"')
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
        match = re.match(rf'{release}-extra\d', r)
        if match is not None:
            filtered.append(r)
    return filtered

def upload_to_archive(fname, counts):
    monthly_archive_name = Path(fname).name
    uploaded = False
    for k in sorted(counts.keys()):
        max_count = 988 if k == 'lgd-archive' else 998
        if counts[k] >= max_count:
            continue
        print(f'uploading {monthly_archive_name} to {k}')
        run_external(f'gh release upload {k} data/combined/{monthly_archive_name}')
        counts[k] += 1
        uploaded = True

    if not uploaded:
        raise Exception(f'No archive available for {monthly_archive_name}, skipping upload')

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
        if prefix_file.exists():
            continue

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

        run_external(f'sh -c "cd {zipping_dir}; 7z a -t7z -mmt=off -m0=lzma2 -mx=9 -ms=on -md=1G -mfb=273 ../combined/{monthly_archive_name} {to_zip_str}"')

        upload_to_archive(f'data/combined/{monthly_archive_name}', archive_counts)
        run_external(f'gh release upload lgd-archive data/combined/{monthly_archive_name}')

        prefix_file.unlink()

        print(f'deleting all unzipped files for {prefix}')
        for p in to_zip:
            p.unlink()

    print('downloading mapping file')
    run_external('gh release download lgd-archive -p archive_mapping.json')

    print('regenerating archive mapping')
    mapping = json.loads(Path('archive_mapping.json').read_text())
    for prefix, dates in by_file.items():
        if prefix not in mapping:
            mapping[prefix] = []
        for d in dates:
            mapping[prefix].append(d)
    for prefix in mapping.keys():
        mapping[prefix] = list(set(mapping[prefix]))

    Path('archive_mapping.json').write_text(json.dumps(mapping))

    print('uploading updated mapping')
    run_external('gh release upload lgd-archive archive_mapping.json --clobber')

    print('deleting already archived files from latest release')
    for asset_name in relevant_names:
        rname = all_archives_mapping[asset_name]
        run_external(f'gh release delete-asset {rname} {asset_name} -y')


    

