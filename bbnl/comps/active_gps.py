import re
import glob
import logging
import shutil
from pathlib import Path

import requests

from .common import (get_url, get_forward_url,
                     get_page_soup, combine_files,
                     get_last_updated_date_subpage,
                     ensure_dir, get_links_from_map_page,
                     parse_pdf_parallel, combine_error_files)

logger = logging.getLogger(__name__)

def get_active_gps(executor, url):
    url = get_url(url)
    url = get_forward_url(url)
    soap = get_page_soup(url)
    #last_updated_date = get_last_updated_date_subpage(soap)
    map_infos = get_links_from_map_page(soap)
    for map_info in map_infos:
        state_name = map_info['title']
        state_url = get_url(map_info['suburl'])
        pdf_file = 'data/raw/activegps/{}.pdf'.format(state_name)
        if Path(pdf_file).exists():
            continue

        ensure_dir(pdf_file)
        logger.info(f'get active gps for state: {state_name}')
        web_data = requests.get(state_url)
        if not web_data.ok:
            raise Exception("unable to retrieve main html for state: {}".format(state_name))
        #print(web_data.text)
        match = re.match(r"<script>window.open\('(.*)','_self'\)</script>", web_data.text)
        if match is None:
            if web_data.text.find("<script>alert('Data Not Available');location.href='actgps.aspx'</script>") == -1:
                raise Exception('Unexpected format of pdf url for state: {}'.format(state_name))
            else:
                logger.warning(f'found empty file for {state_name}')
                with open(pdf_file, 'w') as f:
                    continue
        pdf_url = match.group(1)
        logger.info(f'got pdf url: {pdf_url}')
        web_data = requests.get(pdf_url)
        if not web_data.ok:
            raise Exception("unable to retrieve list pdf for state: {}".format(state_name))
        with open(pdf_file, 'wb') as f:
            f.write(web_data.content)


def validate_active_gps(row):
    if all([ x == '' for x in row]):
        return []
    non_empty = [0, 1, 2, 3, 4]
    errors = []
    for colno in non_empty:
        if row[colno] == '':
            errors.append('col {} not expected to be empty'.format(colno))
    return errors


def transform_active_gps(row, row_id, pno, num_pages, rows):
    if pno == 0 and row_id == 0:
        return False
    expected_len = 6 if pno == 0 or pno == num_pages - 1 else 5
    if len(row) != expected_len:
        logger.warning('unexpected number of cols: {}(expected {}) in row: {}, pno: {}'.format(len(row), expected_len, row_id, pno))
        if len(row) < expected_len:
            row += [''] * (expected_len - len(row))
    return row[:5]


def parse_active_gps(executor):
    combined_out_file = 'data/parsed/active_gps.csv'
    combined_errors_file = 'data/parsed/active_gps.errors.json'
    if Path(combined_out_file).exists():
        logger.info(f'{combined_out_file} already exists.. skipping')
        return
    out_filenames = []
    errors_filenames = []
    filenames = glob.glob('data/raw/activegps/*.pdf')
        

    for filename in filenames:
        logger.info('processing file: {}'.format(filename))
        state_name = Path(filename).stem
        out_filename, errors_filename = parse_pdf_parallel(executor,
                                                           filename,
                                                           validate_active_gps,
                                                           transform_active_gps,
                                                           ignore_empty=True)
        out_filenames.append((out_filename, { 'State': state_name},))
        if errors_filename is not None:
            errors_filenames.append(errors_filename)

    #TODO: combine errors files?
    combine_files(out_filenames, combined_out_file, enrichers={ 'State' : 'State'})
    combine_error_files(errors_filenames, combined_errors_file)
    shutil.rmtree('data/parsed/activegps')
