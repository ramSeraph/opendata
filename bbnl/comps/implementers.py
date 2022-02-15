import csv
import glob
import logging
import shutil
from pathlib import Path

import requests

from .common import (get_url, 
                     get_page_soup,
                     ensure_dir, get_links_from_map_page,
                     parse_pdf_parallel)

logger = logging.getLogger(__name__)

def get_implementers(executor, url):
    logger.info('processing implementers page')
    #url = 'http://www.bbnl.nic.in/index1.aspx?lsid=479&lev=2&lid=392&langid=1'
    #url = 'http://www.bbnl.nic.in/statewise.aspx?langid=1'
    soup = get_page_soup(get_url(url))
    map_infos = get_links_from_map_page(soup)
    dirname = 'data/raw/implementers/'
    for map_info in map_infos:
        suburl = map_info['suburl']
        filename = suburl.split('/')[-1]
        if filename in ['4.pdf', '23.pdf', '24.pdf', '#']: 
            continue
        full_filename = dirname + filename
        if Path(full_filename).exists():
            logger.info(f'{full_filename} already exists.. skipping')
            continue
        ensure_dir(full_filename)
        logger.info(f'processing page: {filename}')
        state_url = get_url(suburl)
        web_data = requests.get(state_url)
        if not web_data.ok:
            raise Exception(f"unable to retrieve implementers page at {suburl}")
        if web_data.headers['Content-Type'] != 'application/pdf':
            logger.info(web_data.headers['Content-Type'])
            #print(web_data.text)
            continue
            #raise Exception(f"unexpected content type when retrieving implementers page at {suburl}")

        with open(full_filename, 'wb') as f:
            f.write(web_data.content)

def transform_implementors(row, row_id, pno, num_pages, rows):
    if all([ x == '' for x in row]):
        return False
    return row

def parse_implementers(executor):
    filenames = glob.glob('data/raw/implementers/*.pdf')
    all_data = []
    for filename in filenames:
        out_filename, _ = parse_pdf_parallel(executor, filename, validator_fn=None, transform_fn=transform_implementors)
        with open(out_filename, 'r') as f:
            reader = csv.reader(f)
            row_id = 0
            data_map = {}
            for row in reader:
                if row_id == 0:
                    header = row[1]
                    header_parts = header.split()
                    phase = header_parts[0]
                    state_name = ' '.join(header_parts[1:])
                    data_map['State'] = state_name
                    data_map['Phase'] = phase
                key = row[3]
                value = row[5]
                data_map[key] = value
                row_id += 1
            all_data.append(data_map)

    out_file = Path('data/parsed/implementers.csv')
    ensure_dir(out_file)

    with open(out_file, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=list(all_data[0].keys()))
        writer.writeheader()
        for entry in all_data:
            writer.writerow(entry)
    shutil.rmtree('data/parsed/implementers')


