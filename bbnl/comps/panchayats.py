import glob
import logging

from concurrent.futures import (wait, ALL_COMPLETED)
from pathlib import Path

import requests

from .common import (get_url, get_page_soup,
                     get_links_from_map_page,
                     drill_down_and_download,
                     parse_pdf_parallel, combine_error_files,
                     combine_files, default_camelot_args)

logger = logging.getLogger(__name__)

def get_panchayats(executor, url):
    main_page_url = 'https://bbnl.nic.in'
    web_data = requests.get(main_page_url)
    if not web_data.ok:
        raise Exception(f'unable to get page {main_page_url}')

    cookies = web_data.headers['Set-Cookie']
    cookie = cookies.split(';')[0]
    soup = get_page_soup(get_url(url))
    map_infos = get_links_from_map_page(soup)
    headers = {
        'Cookie': cookie
    }
    #logger.info(headers)
    for map_info in map_infos:
        logger.info(map_info)
        drill_down_and_download(map_info, headers, 'panchayats')
        

def validate_panchayats(row):
    if all([ x == '' for x in row]):
        return []
    errors = []
    non_empty = [ 0, 1 ]
    for colid in non_empty:
        if row[colid] == '':
            errors.append(f'col {colid} is empty')
    return errors


def transform_panchayats(row, row_id, pno, num_pages, rows):
    expected_len = 2
    if len(row) != expected_len:
        logger.warning('unexpected number of cols: {}(expected {}) in row: {}, pno: {}'.format(len(row), expected_len, row_id, pno))
        if len(row) < expected_len:
            row += [''] * (expected_len - len(row))
    row = row[:expected_len]
    if pno == 0 and row_id == 0:
        if row[0] != 'Gram Panchayat Name':
            logger.warning('adding missing header to file')
            rows.append(['Gram Panchayat Name', 'GP ID'])
    if pno == num_pages - 1:
        if row[1] == '' and row[0].find('Total') != -1:
            return False
    return row


def get_info(filename):
    block_name = Path(filename).stem
    parts = [ p.name for p in Path(filename).parents ][:2]
    state_name = parts[1]
    dist_name = parts[0]
    info = {
        'State': state_name,
        'District': dist_name,
        'Block': block_name,
    }
    return info


def parse_panchayats(executor):
    filenames = glob.glob('data/raw/panchayats/*/*/*.pdf')
    combined_out_file = 'data/parsed/panchayats.csv'
    combined_errors_file = combined_out_file.replace('.csv', '.errors.json')

    if Path(combined_out_file).exists():
        logger.info(f'{combined_out_file} already exists.. skipping')
        return

    ignore_file = Path(__file__).parent.joinpath('panchayats.ignore.txt')
    with open(ignore_file, 'r') as f:
        files_to_ignore = f.readlines()
    files_to_ignore = [ x.strip() for x in files_to_ignore ]
    #files_to_ignore = []

    camelot_args = default_camelot_args
    camelot_args.update({
        'line_scale': 75
    })
    out_filename_entries = []
    errors_filenames = []
    fut_to_fname = {}
    for filename in filenames:
        logger.info(f'processing {filename}')
        if Path(filename).stat().st_size == 0:
            continue

        if filename in files_to_ignore:
            logger.warning(f'ignoring problematic file - {filename}')
            continue

        fut = parse_pdf_parallel(executor,
                                 filename,
                                 validate_panchayats,
                                 transform_panchayats,
                                 flavor_order=['lattice'],
                                 merge_tables='v',
                                 camelot_args=camelot_args,
                                 deferred=True)
        fut_to_fname[fut] = filename
       
    done, not_done = wait(fut_to_fname, return_when=ALL_COMPLETED)
    if len(done) != len(fut_to_fname):
        raise Exception('Some pages weren\'t parsed')

    has_errors = False
    for fut in done:
        fname = fut_to_fname[fut]
        try:
            out_filename, errors_filename = fut.result()
        except Exception:
            logger.exception(f'{fname} parsing failed')
            has_errors = True
        info = get_info(fname)
        out_filename_entries.append((out_filename, info))
        if errors_filename != None:
            errors_filenames.append(errors_filename)
 
    if has_errors:
        raise Exception(f'parsing failed for {filename}')


    combine_files(out_filename_entries, combined_out_file,
                  enrichers = {'State' : 'State', 'District': 'District', 'Block': 'Block'})
    combine_error_files(errors_filenames, combined_errors_file,
                        key_fn=lambda fname: '.'.join(get_info(fname).values()))



