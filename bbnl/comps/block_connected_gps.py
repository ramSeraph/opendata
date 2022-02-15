import logging
from pathlib import Path

import requests

from .common import (get_url, parse_pdf_parallel)

logger = logging.getLogger(__name__)

def get_block_connected_gps(exxecutor, url):
    pdf_file = 'data/raw/block_connected_gps.pdf'
    if Path(pdf_file).exists():
        return
    url = get_url(url)
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception("unable to retrieve block connected gps")
    with open(pdf_file, 'wb') as f:
        f.write(web_data.content)


def validate_block_connected_gps(row):
    if all([ x == '' for x in row]):
        return []
    errors = []
    non_empty = [ 0, 1, 2, 3, 4 ]
    for colid in non_empty:
        if row[colid] == '':
            errors.append(f'col {colid} is empty')
    return errors

def transform_block_connected_gps(row, row_id, pno, num_pages, rows):
    if pno == 0 and row_id == 0:
        return False
    expected_len = 5
    if len(row) != expected_len:
        logger.warning('unexpected number of cols: {}(expected {}) in row: {}, pno: {}'.format(len(row), expected_len, row_id, pno))
        if len(row) < expected_len:
            row += [''] * (expected_len - len(row))
    row = row[:expected_len]
    if row[3] == '':
        prev_col = rows[-1][3]
        logger.warning(f'filling empty column 4 with prev column value {prev_col}')
        row[3] = prev_col
    return row


def parse_block_connected_gps(executor):
    pdf_file = 'data/raw/block_connected_gps.pdf'
    parse_pdf_parallel(executor, pdf_file, validate_block_connected_gps, transform_block_connected_gps)


