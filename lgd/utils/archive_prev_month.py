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


def get_all_archive_names():
    run_external('sh -c "gh release view lgd-latest --json assets > release.json"')
    rfile = Path('release.json')
    data = json.loads(rfile.read_text())
    assets = data['assets']
    fnames = [ a['name'] for a in assets ]
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

if __name__ == '__main__':
    import sys

    month_year = sys.argv[1]

    all_archives = get_all_archive_names()

    relevant_names = [ a for a in all_archives if a.endswith(f'{month_year}.csv.7z') ]

    by_file = get_mapping(relevant_names)

    zipping_dir = Path('data/zipping_area')
    zipping_dir.mkdir(exist_ok=True, parents=True)

    for prefix, dates in by_file.items():
        to_zip = []

        prefix_file = Path('data/combined/{prefix}.{month_year}.7z')
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
            run_external(f'gh release download lgd-latest -p {zname} -D {zipping_dir}')

            print(f'extracting {zname}')
            run_external(f'sh -c "cd {zipping_dir}; 7z e {zname}"')

            print(f'deleting {zfile}')
            zfile.unlink()

            to_zip.append(file)

        to_zip_str = ' '.join([f.name for f in to_zip])

        run_external(f'sh -c "cd {zipping_dir}; 7z a -t7z -mmt=off -m0=lzma2 -mx=9 -ms=on -md=1G -mfb=273 ../combined/{prefix}.{month_year}.7z {to_zip_str}"')

        print(f'deleting all unzipped files for {prefix}')
        for p in to_zip:
            p.unlink()

    print('uploading files')
    run_external('gh release upload lgd-archive data/combined/*')

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

    #print('deleting already archived files from latest release')
    #for asset_name in relevant_names:
    #    run_external(f'gh release delete-asset lgd-latest {asset_name} -y')


    

