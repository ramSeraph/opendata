#!/usr/bin/env -S uv run 
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pygithub",
#     "requests",
#     "numpy",
#     "opencv-python-headless",
#     "pdfminer-six",
#     "pillow",
#     "pypdf",
#     "scipy",
# ]
# ///

import json
import shutil
import requests
from pathlib import Path
from github import Auth, Github

from convert import Converter, get_extra, run_external


gh_api = None
def get_github_api():
    global gh_api

    if gh_api is not None:
        return gh_api

    token_file = Path(__file__).parent / 'token.txt'
    token = token_file.read_text().strip()
    auth = Auth.Token(token)
    gh_api = Github(auth=auth)
    return gh_api

def upload_file(repo_name, release, file):
    gh = get_github_api()
    user = gh.get_user()
    github_repo = gh.get_repo(f"{user.login}/{repo_name}")
    release_obj = github_repo.get_release(release)
    release_obj.upload_asset(
        path=str(file),
        content_type='application/octet-stream',
        name=file.name
    )


def get_pdfs():
    lines = Path('listing_pdfs.txt').read_text().split('\n')
    pdfs = [ line.strip('\n').split(' ')[1] for line in lines if line.strip('\n') != '']
    pdfs = [ p for p in pdfs if not p.endswith('.unavailable') ]
    return pdfs

download_dir = Path('data/raw')

done_list = 'done.txt'

def download_from_gcs(p):
    out_file = download_dir / f'{p}.pdf'
    if out_file.exists():
        return out_file
    resp = requests.get(f'https://storage.googleapis.com/soi_data/raw/{p}.pdf')
    if not resp.ok:
        raise Exception(f'unable to download {p}')
    
    out_file.write_bytes(resp.content)
    return out_file

def download_from_github(p):
    out_file = download_dir / f'{p}.pdf'
    if out_file.exists():
        return out_file
    resp = requests.get(f'https://github.com/ramSeraph/opendata/releases/download/soi-pdfs/{p}.pdf')
    if not resp.ok:
        raise Exception(f'unable to download {p}')
    
    out_file.write_bytes(resp.content)
    return out_file

def add_to_done(p):
    with open('done.txt', 'a') as f:
        f.write(p)
        f.write('\n')

def get_done_list():
    done_file = Path('done.txt')
    if not done_file.exists():
        return set()
    lines = done_file.read_text().split('\n')
    lines = [ li.strip() for li in lines ]
    lines = [ li for li in lines if li != '' ]
    return set(lines)

if __name__ == '__main__':
    pdfs = get_pdfs()
    num_pdfs = len(pdfs)
    done_set = get_done_list()
    num_done = len(done_set)

    special_cases = {}
    special_cases_file = Path(__file__).parent.joinpath('special_cases.json')
    if special_cases_file.exists():
        special_cases = json.loads(special_cases_file.read_text())


    for p in pdfs:
        if p in done_set:
            continue
        print(f'downloading {p} {num_done}/{num_pdfs}')
        file = download_from_gcs(p)
        extra, extra_ancillary = get_extra(special_cases, str(file))
        converter = Converter(str(file), extra, extra_ancillary)
        print(f'converting {p}')
        converter.convert()
        print(f'compressing {p}')
        converter.compress()
        converter.close()
        run_external(f'gsutil cp data/inter/{p}/compressed.jpg gs://soi_data/compressed/{p}.jpg') 
        shutil.rmtree(f'data/inter/{p}')
        print(f'uploading {p}')
        #upload_file('opendata', 'soi-pdfs', file)
        file.unlink()
        add_to_done(p)
        num_done += 1

