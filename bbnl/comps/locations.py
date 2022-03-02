import csv
import glob
import logging
import shutil

from pathlib import Path

import requests

from xlsx2csv import Xlsx2csv

from .common import (get_url, ensure_dir,
                     get_page_soup, combine_files,
                     parse_pdf_parallel, delete_files,
                     combine_error_files, default_camelot_args)

logger = logging.getLogger(__name__)

def get_locations(executor, url):
    # from Navigation
    #url = 'http://www.bbnl.nic.in/index1.aspx?langid=1&lev=2&lsid=655&pid=2&lid=526'
    # from New Ticker
    #url = 'http://www.bbnl.nic.in/index1.aspx?lsid=652&lev=2&lid=526&langid=1'

    soup = get_page_soup(get_url(url))
    div = soup.find('div', { 'id': "maincontaint_main_display" })
    table = div.find('table', { 'class': "MsoTableGrid" })
    rows = table.find_all('tr')

    state_infos = {}
    for i, row in enumerate(rows):
        if i == 0:
            continue
        cols = row.find_all('td')
        if len(cols) != 4:
            raise Exception('unexpected number of cols - {} for row - {}'.format(len(cols), i))
    
        elem = cols[1].find('span')
        if elem is None:
            elem = cols[1].find('font')
        state_name = elem.text
        link = cols[2].find('a')
        url1 = None
        if link is not None:
            url1 = link.attrs['href']
        link = cols[3].find('a')
        url2 = None
        if link is not None:
            url2 = link.attrs['href']
        state_infos[state_name] = {
            "FPOIs": url1,
            "OLTs": url2
        }
    logger.info(state_infos)

    def get_page(p_url, pdf_file_name):
        logger.info('writing {} to {}'.format(p_url, pdf_file_name))
        xlsx_file_name = pdf_file_name.replace('.pdf', '.xlsx')
        if Path(pdf_file_name).exists() or Path(xlsx_file_name).exists():
            return

        web_data = requests.get(p_url)
        if not web_data.ok:
            raise Exception("unable to retrieve locations state page")

        ensure_dir(pdf_file_name)
        if web_data.headers['Content-Type'] == 'application/pdf; charset=utf-8':
            logger.info(f'writing {pdf_file_name}')
            with open(pdf_file_name, 'wb') as f:
                f.write(web_data.content)
            return

        logger.info(f'writing {xlsx_file_name}')
        with open(xlsx_file_name, 'wb') as f:
            f.write(web_data.content)
        

    for state_name, info in state_infos.items():
        if info['FPOIs'] is not None:
            get_page(info['FPOIs'], 'data/raw/locations/{}/FPOIs.pdf'.format(state_name))
        if info['OLTs'] is not None:
            get_page(info['OLTs'], 'data/raw/locations/{}/OLTs.pdf'.format(state_name))


def split_FPOI_file(filename):
    fpoi_filename = Path(filename).with_stem('FPOI_locations')
    gp_filename = Path(filename).with_stem('GP_locations')
    logger.info(f'splitting {filename} into {fpoi_filename} and {gp_filename}')

    fpoi_rows = []
    gp_rows = []
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            row = [ x.replace('\n', '').strip() for x in row ]
            gp_row = row[:6]
            if not all([x == '' for x in gp_row]):
                gp_rows.append(gp_row)

            fpoi_row = row[7:]

            # add empty name column if it doesn't exist
            if len(fpoi_row) == 3:
                to_add = 'Name' if len(fpoi_rows) == 0 else ''
                fpoi_row = fpoi_row[:1] + [to_add] + fpoi_row[1:]

            if all([x == '' for x in fpoi_row]):
                continue

            # gather BLOCK and DISTRICT fields
            # if first row or block name changed pick from gp_row
            # otherwise pick from previous enhanced fpoi row
            if len(fpoi_rows) == 0 or fpoi_rows[-1][2] != fpoi_row[0]:
                fpoi_row_ex = [gp_row[0], gp_row[1]]
            else:
                fpoi_row_ex = [fpoi_rows[-1][0], fpoi_rows[-1][1]]
            fpoi_row_ex.extend(fpoi_row)
            fpoi_rows.append(fpoi_row_ex)

    with open(fpoi_filename, 'w') as f:
        wr = csv.writer(f)
        for row in fpoi_rows:
            wr.writerow(row)

    with open(gp_filename, 'w') as f:
        wr = csv.writer(f)
        for row in gp_rows:
            wr.writerow(row)

    return gp_filename, fpoi_filename
            

def validate_FPOIs(row):
    non_empty_cols = [0, 1, 2, 3, 4, 5]
    empty_cols = [6]
    non_empty_together = [7, 8, 9]

    if all([ x == '' for x in row]):
        return []

    errors = []
    for colno in non_empty_cols:
        if row[colno] == '':
            errors.append('col {} not expected to be empty'.format(colno))
    for colno in empty_cols:
        if row[colno] != '':
            errors.append('col {} expected to be empty but has "{}"'.format(colno, row[colno]))

    non_empty_together_cols = [ row[x] for x in non_empty_together ]
    non_empty_together_cols_check = [ x == '' for x in non_empty_together_cols ]
    if not all(non_empty_together_cols_check) and any(non_empty_together_cols_check):
        errors.append('cols {} expected to be empty together {}'.format(non_empty_together, non_empty_together_cols))
    return errors



def transform_FPOIs(row, row_id, pno, num_pages, rows):
    if pno == 0:
        if row_id == 0:
            row_str = ' '.join(row).lower()
            if not row_str.startswith('state'):
                return False
        elif row_id == 1:
            row_str = ' '.join(row).lower()
            if row_str.startswith('gp_details'):
                return False

    if all([ x == '' for x in row]):
        return False
    expected_len = 10
    if len(row) != expected_len:
        logger.warning('unexpected number of cols: {}(expected {}) in row: {}, pno: {}'.format(len(row), expected_len, row_id, pno))
        if len(row) < expected_len:
            row += [''] * (expected_len - len(row))

    def fix_col(colno):
        if colno > 0:
            prev_lines = row[colno - 1].split('\n')
            if len(prev_lines) > 1 and prev_lines[-1].strip() != '':
                row[colno - 1] = '\n'.join(prev_lines[:-1])
                row[colno] = prev_lines[-1].strip()
                logger.warning('copying line {} col from {} to {}'.format(row[colno], colno - 1, colno))
 
    non_empty_cols = [0, 1, 2, 3, 4, 5]
    non_empty_together = [7, 8, 9]
 

    for colno in non_empty_cols:
        if row[colno] == '':
            fix_col(colno)

    non_empty_together_cols = [ row[x] for x in non_empty_together ]
    non_empty_together_cols_check = [ x == '' for x in non_empty_together_cols ]
    if not all(non_empty_together_cols_check) and any(non_empty_together_cols_check):
        for colno in non_empty_together:
            if row[colno] == '':
                fix_col(colno)
    
    return row[:expected_len]


def parse_FPOIs(executor):
    filenames = glob.glob('data/raw/locations/*/FPOIs.pdf')
    xlsx_filenames = glob.glob('data/raw/locations/*/FPOIs.xlsx')

    combined_gp_locations_file = 'data/parsed/GP_locations.csv'
    combined_fpoi_locations_file = 'data/parsed/FPOI_locations.csv'
    combined_errors_file = 'data/parsed/FPOI_locations.errors.json'

    if Path(combined_gp_locations_file).exists():
        logging.info(f'{combined_gp_locations_file} exists.. skipping')
        return

    out_filenames = []
    errors_filenames = []
    for filename in xlsx_filenames:
        logger.info('processing file: {}'.format(filename))

        csv_file_name = filename.replace('/raw/', '/parsed/')
        csv_file_name = csv_file_name.replace('.xlsx', '.csv')
        out_filenames.append(csv_file_name)
        if Path(csv_file_name).exists():
            logger.info(f'{csv_file_name} exists.. skipping')
            continue
        ensure_dir(csv_file_name)
        Xlsx2csv(filename, outputencoding="utf-8").convert(csv_file_name)
        csv_file_name_new = csv_file_name + '.new'
        rows = []
        with open(csv_file_name, 'r') as f:
            reader = csv.reader(f)
            row_id = 0
            for row in reader:
                if row_id == 0 or row_id == 1:
                    row_id += 1
                    logger.info(f'dropping row: {row}')
                    continue
                row = [ x.replace('\n', '').strip() for x in row ]
                if all([ x == '' for x in row ]):
                    row_id += 1
                    continue
                row = row[:11]
                rows.append(row)
                row_id += 1
        logger.info(f'dropping rows: {rows[-3:]}')
        rows = rows[:-3]

        logger.info(f'writing file {csv_file_name_new}')
        with open(csv_file_name_new, 'w') as out_f:
            wr = csv.writer(out_f)
            for row in rows:
                wr.writerow(row)
        logger.info(f'moving file {csv_file_name_new} to {csv_file_name}')
        Path(csv_file_name_new).replace(csv_file_name)


    camelot_args = default_camelot_args
    camelot_args.update({
        'strip_text': '',
    })
    for filename in filenames:
        logger.info('processing file: {}'.format(filename))

        # these are actually OLT location pdfs wrongly filed under FPOI
        if filename in ['data/raw/locations/Assam/FPOIs.pdf','data/raw/locations/Karnataka/FPOIs.pdf']:
            logger.warning(f'skipping {filename} because of known problems')
            continue

        out_filename, errors_filename = parse_pdf_parallel(executor,
                                                           filename,
                                                           validate_FPOIs,
                                                           transform_FPOIs,
                                                           merge_tables=True,
                                                           discard_overlapping=False,
                                                           camelot_args=camelot_args)
        out_filenames.append(out_filename)
        if errors_filename is not None:
            errors_filenames.append(errors_filename)

    gp_locations_files = []
    fpoi_locations_files = []
    for filename in out_filenames:
        gp_locations_file, fpoi_locations_file = split_FPOI_file(filename)
        gp_locations_files.append(gp_locations_file)
        fpoi_locations_files.append(fpoi_locations_file)

    combine_error_files(errors_filenames, combined_errors_file, key_fn=lambda fname: Path(fname).parent.name)

    combine_files(fpoi_locations_files, combined_fpoi_locations_file)
    combine_files(gp_locations_files, combined_gp_locations_file)

    folder_name = 'data/parsed/locations'
    #logger.info(f'deleting folder {folder_name}')
    #shutil.rmtree(folder_name)


def validate_OLTs(row):
    if all([ x == '' for x in row]):
        return []
    errors = []
    non_empty_fields = [0, 1, 2, 3]
    if not all([ x == '' for x in row[4:]]):
        non_empty_fields = [0, 1, 2, 3, 4, 5]
    for colno in non_empty_fields:
        if row[colno] == '':
            errors.append('col {} not expected to be empty'.format(colno))
    return errors


def transform_OLTs(row, row_id, pno, num_pages, rows):
    if pno == 0 and row_id == 0 and not ' '.join(row).lower().startswith('state'):
        return False
    expected_len = 6
    if len(row) != expected_len:
        logger.warning('unexpected number of cols: {}(expected {}) in row: {}, pno: {}'.format(len(row), expected_len, row_id, pno))
        if len(row) < expected_len:
            row += [''] * (expected_len - len(row))
    return row[:expected_len]


def parse_OLTs(executor):

    combined_file = 'data/parsed/OLT_locations.csv'
    combined_errors_file = 'data/parsed/OLT_locations.errors.json'

    if Path(combined_file).exists():
        logger.info(f'{combined_file} exists.. skipping')
        return

    filenames = glob.glob('data/raw/locations/*/OLTs.pdf')
    xlsx_filenames = glob.glob('data/raw/locations/*/OLTs.xlsx')
    out_filenames = []
    errors_filenames = []
    for filename in filenames:
        logger.info('processing file: {}'.format(filename))
        out_filename, errors_filename = parse_pdf_parallel(executor,
                                                           filename,
                                                           validate_OLTs,
                                                           transform_OLTs)
        out_filenames.append(out_filename)
        if errors_filename is not None:
            errors_filenames.append(errors_filename)

    for filename in xlsx_filenames:
        logger.info('processing file: {}'.format(filename))

        csv_file_name = filename.replace('/raw/', '/parsed/')
        csv_file_name = csv_file_name.replace('.xlsx', '.csv')
        out_filenames.append(csv_file_name)
        if Path(csv_file_name).exists():
            logger.info(f'{csv_file_name} exists.. skipping')
            continue
        ensure_dir(csv_file_name)
        Xlsx2csv(filename, outputencoding="utf-8").convert(csv_file_name)

    for filename in out_filenames:
        logger.info(f'converting {filename}')
        # doesn't contain location information
        if filename in [ 'data/parsed/West Bengal/OLTs.csv' ]:
            logger.warning(f'ignoring problematic file {filename}')
            continue
        filename_new = filename + '.new'
        override_state = False
        state_name = Path(filename).parent.name
        logger.info(f'state name: {state_name}')
        with open(filename_new, 'w') as out_f:
            wr = csv.writer(out_f)
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                rowid = 0
                for row in reader:
                    row = [x.strip() for x in row]
                    row = [x.replace('\n', ' ') for x in row]
                    is_empty = all([x == '' for x in row])
                    if is_empty \
                            or row[0].find('http://www.bbnl.nic.in') != -1 \
                            or row[0].find('The OLT Names highlighted in red') != -1:
                        rowid += 1
                        continue
                    if rowid == 0:
                        if row[0].lower().strip() != 'state':
                            override_state = True
                            row[0] = 'State'
                            logging.info('overriding state')
                    else:
                        if override_state:
                            row[0] = state_name
                    wr.writerow(row)
                    rowid += 1
        Path(filename_new).replace(filename)
            
    combine_files(out_filenames, combined_file)
    combine_error_files(errors_filenames, combined_errors_file)
    delete_files(out_filenames)


def parse_locations(executor):
    parse_OLTs(executor)
    parse_FPOIs(executor)


