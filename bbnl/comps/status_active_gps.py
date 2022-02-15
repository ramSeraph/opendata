import csv
import copy
import json
import glob
import logging

from pathlib import Path
from concurrent.futures import (wait, ALL_COMPLETED)

import requests
import camelot

from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader, PdfFileWriter
from pdfminer.layout import LTRect
from camelot.utils import (get_page_layout, text_in_bbox,
                           random_string, TemporaryDirectory)

from .common import (monkeypatch_camelot, ensure_dir,
                     combine_files, combine_error_files, DEBUG)


logger = logging.getLogger(__name__)

def get_status_active_gps(executor, url):
    url = 'http://www.bbnl.nic.in/index1.aspx?lsid=808&lev=2&lid=643&langid=1'
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception("unable to retrieve locations main page")
    soup = BeautifulSoup(web_data.text, 'html.parser')
    div = soup.find('div', { 'id': "maincontaint_main_display" })
    ps = div.find_all('p', { 'class': "MsoNormal" })
    for p in ps:
        spans = p.find_all('span')
        link = None
        text = ''
        for span in spans:
            a = span.find('a')
            text += span.text
            if a is not None:
                link = a['href']

        if link is None:
            raise Exception('unable to find link in spans')
        state_name = text.replace('Click Here: FOR', '').split('.')[1].strip()
        logger.info(f'state_name: {state_name}, link: {link}')
        pdf_filename = f'data/raw/active_gp_status/{state_name}.pdf'
        if Path(pdf_filename).exists():
            logger.info(f'found {pdf_filename}.. skipping')
            continue
        web_data = requests.get(link)
        if not web_data.ok:
            raise Exception(f"unable to retrieve status page for state {state_name}")
        content_type = web_data.headers['Content-Type'] 
        if content_type != 'application/pdf; charset=utf-8':
            raise Exception(f'unexpected content-type while downloading status page for state {state_name}, content-type: {content_type}')
        directory = Path(pdf_filename).parent
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
        with open(pdf_filename, 'wb') as f:
            f.write(web_data.content)



def validate_status_active_gps(row):
    if all([ x == '' for x in row]):
        return []
    non_empty = [0, 1, 2, 3]
    errors = []
    for colno in non_empty:
        if row[colno] == '':
            errors.append('col {} not expected to be empty'.format(colno))
    return errors


def get_bbox_first_row(table):
    first_row = table.cells[0]

    row_bbox = None
    for cell in first_row:
        if row_bbox is None:
            row_bbox = [cell.x1, cell.y1, cell.x2, cell.y2]
        if cell.x1 < row_bbox[0]:
            row_bbox[0] = cell.x1
        if cell.y1 < row_bbox[1]:
            row_bbox[1] = cell.y1
        if cell.x2 > row_bbox[2]:
            row_bbox[2] = cell.x2
        if cell.y2 > row_bbox[3]:
            row_bbox[3] = cell.y2
    return row_bbox


def get_rect_objs(layout):
    t = []
    try:
        for obj in layout._objs:
            if isinstance(obj, LTRect):
                t.append(obj)
            else:
                t += get_rect_objs(obj)
    except AttributeError:
        pass
    return t


def table_has_header(page_filename, table):
    layout, dim = get_page_layout(page_filename)
    rect_objs = get_rect_objs(layout)

    bbox_first_row = get_bbox_first_row(table)
    first_row_rects = text_in_bbox(bbox_first_row, rect_objs)

    is_header = False
    header_color = (1.0, 1.0, 0.0) # yellow
    for rect in first_row_rects:
        if rect.non_stroking_color == header_color:
            is_header = True
            break
    return is_header

def parse_status_active_gps_page(filename, pno, num_pages, page_filename, output_filename):
    logger.info('processing page {}/{}'.format(pno, num_pages - 1))
    output_filename_page = output_filename + f'.{pno}'
    has_header_filename_page = filename + f'.has_header.{pno}'

    ret = [output_filename_page, has_header_filename_page]
    if Path(output_filename_page).exists(): 
        logger.info(f'{output_filename_page} already exists.. skipping')
        if not Path(has_header_filename_page).exists():
            ret[1] = None
        return ret

    filesize = Path(page_filename).stat().st_size
    logger.info(f'using {page_filename} - {filesize}')
    # Try stream when lattice parser fails
    success = False
    for flavor in [ 'lattice', 'stream' ]:
        if success:
            break
        logger.info(f'using {flavor} flavor')
        has_header = False
        
        tables = camelot.read_pdf(page_filename,
                                  backend='poppler',
                                  pages='1',
                                  flavor=flavor,
                                  #layout_kwargs=laparams,
                                  #discard_overlapping=False,
                                  strip_text='\n',
                                  split_text=True)
                                 
        num_tables = len(tables)
        logger.info(f'got {num_tables} tables') 
        if num_tables != 1:
            logger.warning('has unexpected number of tables')
            continue
        if DEBUG:
            from imgcat import imgcat
            import matplotlib
            matplotlib.use("module://imgcat")
            for table in tables:
                plt = camelot.plot(table, kind='text')
                plt.show()
                plt = camelot.plot(table, kind='grid')
                plt.show()
                plt = camelot.plot(table, kind='contour')
                plt.show()
                if flavor != 'stream':
                    plt = camelot.plot(table, kind='line')
                    plt.show()
                    plt = camelot.plot(table, kind='joint')
                    plt.show()
                logger.info(f'table bbox: {table._bbox}')
                for direction in [ 'horizontal', 'vertical' ]:
                    logger.info(f't_bbox - {direction}')
                    text = table._t_bbox[direction]
                    for t in text:
                        logger.info(f'text: {t}')
                for row in table.cells:
                    for cell in row:
                        logger.info(f'cell: {cell} {cell.text}')


        table = tables[0]
        data = copy.copy(table.data)
        logger.info(f'got data: {data}')

        if len(data) == 0:
            has_header = False
        else:
            has_header = table_has_header(page_filename, table)
        success = True

    if num_tables != 1:
        raise Exception('unexpected number of tables')

    if has_header:
        logger.info(f'writing file {has_header_filename_page}')
        with open(has_header_filename_page, 'w'):
            pass
    else:
        ret[1] = None

    logger.info(f'writing file {output_filename_page}')
    with open(output_filename_page, 'w') as f:
        csv_writer = csv.writer(f)
        for row in data:
            csv_writer.writerow(row)
    return ret


def parse_status_active_gps(executor):
    filenames = glob.glob('data/raw/active_gp_status/*.pdf')
    #filenames = [ 'data/raw/active_gp_status/ANDHRA PRADESH.pdf' ]

    monkeypatch_camelot()

    combined_output_file = 'data/parsed/active_gp_status.csv'
    combined_errors_file = combined_output_file.replace('.csv', '.errors.json')

    if Path(combined_output_file).exists():
        logger.info(f'{combined_output_file} exists.. skipping')
        return

    final_output_filenames = []
    final_errors_filenames = []
    with TemporaryDirectory() as tempdir:
        for filename in filenames:
            logger.info(f'parsing {filename}')

            output_filename = filename.replace('/raw/', '/parsed/')
            output_filename = output_filename.replace('.pdf', '.csv')

            errors_filename = filename.replace('/raw/', '/parsed/')
            errors_filename = errors_filename.replace('.pdf', '.errors.json')

            final_output_filenames.append(output_filename)
            final_errors_filenames.append(errors_filename)
            if Path(output_filename).exists(): 
                logger.info(f'{output_filename} already exists.. skipping')
                continue

            ensure_dir(output_filename)
            page_map = {}
            with open(filename, "rb") as f:
                pdf_reader = PdfFileReader(f, strict=False)
                num_pages = pdf_reader.numPages
                for pno in range(num_pages):
                    page_map[pno] = pdf_reader.getPage(pno)


                output_filenames = {}
                has_header_filenames = {}
                fut_to_pno = {}
                for pno in range(num_pages):
                    #if pno != 165:
                    #    continue
                    temp_page_file = Path(tempdir).joinpath(f'{random_string(6)}.pdf')
                    pdf_writer = PdfFileWriter()
                    pdf_writer.addPage(page_map[pno])
                    with open(temp_page_file, "wb") as f:
                        pdf_writer.write(f)
                    page_filename = f.name

                    fut = executor.submit(parse_status_active_gps_page,
                                          filename, pno, num_pages,
                                          page_filename, output_filename)
                    fut_to_pno[fut] = pno
            done, not_done = wait(fut_to_pno, return_when=ALL_COMPLETED)
            if len(done) != len(fut_to_pno):
                raise Exception('Some pages weren\'t parsed')

            has_errors = False
            for fut in done:
                pno = fut_to_pno[fut]
                try:
                    ret = fut.result()
                    output_filenames[pno] = ret[0]
                    if ret[1] != None:
                        has_header_filenames[pno] = ret[1]
                except Exception:
                    logger.exception(f'{pno} parsing failed')
                    has_errors = True

            if has_errors:
                logger.error('some of the page parsing failed.. not collating pages')
                return


            logger.info('collating pages')
            sections = []
            section = None
            pnos = sorted(output_filenames.keys())
            expected_len = None
            for pno in pnos:
                filename = output_filenames[pno]
                has_header = pno in has_header_filenames
                logger.info(f'collecting data form {filename}, has_header: {has_header}')
                with open(filename, 'r') as f:
                    csv_reader = csv.reader(f)
                    rowid = 0
                    for row in csv_reader:
                        if rowid == 0:
                            if has_header:
                                expected_len = len(row)
                                if section is not None:
                                    sections.append(section)
                                logger.info('starting new section')
                                section = []

                        if expected_len is None:
                            raise Exception('initial header not found')

                        if len(row) != expected_len:
                            logger.warning('unexpected number of cols: {} in row: {}, pno: {}'.format(len(row), rowid, pno))
                            logger.warning(row)
                            if len(row) < expected_len:
                                row += [''] * (expected_len - len(row))
                        section.append((row, pno, rowid))
                        rowid += 1

            if section is not None:
                sections.append(section)
            logger.info(f'num sections: {len(sections)}')
            # make sure all sections have same no of rows
            section_len = None
            for section in sections:
                if section_len is None:
                    section_len = len(section)

                if len(section) != section_len:
                    raise Exception(f'current section len {len(section)} didn\'t match prev len {section_len}') 

            def join_rows(*rows):
                out_row = []
                out_pnos = []
                out_rowids = []
                for row, pno, rowid in rows:
                    out_row.extend(row)
                    out_pnos.append(pno)
                    out_rowids.append(rowid)
                return out_row, out_pnos, out_rowids

            all_data_with_pnos = map(join_rows, *sections)
            all_data = []
            all_errors = {}
            for row, pnos, rowids in all_data_with_pnos:
                all_data.append(row)
                errors = validate_status_active_gps(row)
                if len(errors) != 0:
                    pnos_str = ','.join([str(x) for x in pnos])
                    rowids_str = ','.join([str(x) for x in rowids])
                    logger.warning('for {}, found validation errors for row - {}: {}'.format(pnos_str, rowids_str, errors))
                    logger.warning(row)
                    all_errors[pnos_str][rowids_str] = errors

            if len(all_errors) > 0:
                logger.info(f'writing file {errors_filename}')
                with open(errors_filename, 'w') as f:
                    json.dump(all_errors, f, indent=4)

            logger.info(f'writing file {output_filename}')
            with open(output_filename, 'w') as f:
                csv_writer = csv.writer(f)
                for row in all_data:
                    csv_writer.writerow(row)

            files_to_delete = list(output_filenames.values()) + list(has_header_filenames.values())
            logger.info(f'deleting files: {files_to_delete}')
            for filename in files_to_delete:
                Path(filename).unlink()

    combine_files(final_output_filenames, combined_output_file)
    combine_error_files(final_errors_filenames, combined_errors_file)
    #shutil.rmtree('data/parsed/active_gp_status')

