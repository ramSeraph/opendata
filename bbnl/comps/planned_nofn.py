import logging

from pathlib import Path

import requests

from .common import (get_url, ensure_dir,
                     parse_pdf_parallel,
                     default_camelot_args)


logger = logging.getLogger(__name__)

def get_planned_nofn(executor, url):
    pdf_file = 'data/raw/planned_nofn.pdf'
    if Path(pdf_file).exists():
        logger.info(f'{pdf_file} exists.. skipping')
        return
    web_data = requests.get(get_url(url))
    if not web_data.ok:
        raise Exception(f"unable to retrieve page {url}")
    ensure_dir(pdf_file)
    logger.info(f'writing {pdf_file}')
    with open(pdf_file, 'wb') as f:
        f.write(web_data.content)

def validate_planned_nofn(row):
    non_empty = [0, 1, 2, 3, 4]
    errors = []
    for colno in non_empty:
        if row[colno] == '':
            errors.append('col {} not expected to be empty'.format(colno))
    return errors


def transform_planned_nofn(row, row_id, pno, num_pages, rows):
    if pno == 0:
        return False
    first_col = row[0].strip()
    if first_col.startswith('Total') or first_col.startswith('Grand Total'):
        return False
    all_empty = all([ x == '' for x in row])
    if all_empty:
        return False
    if row[0] != '' and all([ x == '' for x in row[1:]]):
        return False

    if row[4] == '':
        #row[4] = rows[-1][4]
        logger.warning('found a row with empty count column, setting spanning count value to 0')
        logger.warning(row)
        row[4] = '0'

    expected_len = 5
    if len(row) != expected_len:
        logger.warning('unexpected number of cols: {}(expected {}) in row: {}, pno: {}'.format(len(row), expected_len, row_id, pno))
        if len(row) < expected_len:
            row += [''] * (expected_len - len(row))
    expected_len = 5
    return row[:expected_len]

        
def parse_planned_nofn(executor):
    pdf_file = 'data/raw/planned_nofn.pdf'
    out_filename = pdf_file.replace('/raw/', '/parsed/')
    out_filename = out_filename.replace('.pdf', '.csv')
    camelot_args = default_camelot_args
    camelot_args.update({
        'line_scale': 75
    })
    out_filename, errors_filename = parse_pdf_parallel(executor,
                                                       pdf_file,
                                                       validate_planned_nofn,
                                                       transform_planned_nofn,
                                                       #flavor_order=['stream', 'lattice'],
                                                       flavor_order=['lattice', 'stream'],
                                                       merge_tables=False,
                                                       camelot_args=camelot_args)




