import os
import re
import csv
import json
import copy
import tempfile
import logging
import shutil

from pathlib import Path
from datetime import datetime
from concurrent.futures import (Future, wait, ALL_COMPLETED)

import requests
import camelot

from camelot.utils import random_string
from PyPDF2 import PdfFileReader, PdfFileWriter
from bs4 import BeautifulSoup

DEBUG = (os.environ.get('DEBUG', None) == '1')

logger = logging.getLogger(__name__)

discard_overlapping_val = True
camelot_monkeypatched = False

def set_discard_overlapping(val):
    global discard_overlapping_val
    discard_overlapping_val = val

def get_discard_overlapping():
    global discard_overlapping_val
    return discard_overlapping_val


def text_in_bbox_keep_overlap(bbox, text):
    lb = (bbox[0], bbox[1])
    rt = (bbox[2], bbox[3])
    t_bbox = [
        t
        for t in text
        if lb[0] - 2 <= (t.x0 + t.x1) / 2.0 <= rt[0] + 2
        and lb[1] - 2 <= (t.y0 + t.y1) / 2.0 <= rt[1] + 2
    ]
    text_set = {t for t in t_bbox}
    return list(text_set)


# monkey patch camelot
def monkeypatch_camelot():
    global camelot_monkeypatched
    if camelot_monkeypatched:
        return
    old_generate_table_func = camelot.parsers.Lattice._generate_table
    def new_generate_table_func(self, table_idx, cols, rows, **kwargs):
        if not get_discard_overlapping():
            tk = sorted(self.table_bbox.keys(), key=lambda x: x[1], reverse=True)[table_idx]
            t_bbox = {}
            t_bbox["horizontal"] = text_in_bbox_keep_overlap(tk, self.horizontal_text)
            t_bbox["vertical"] = text_in_bbox_keep_overlap(tk, self.vertical_text)
    
            t_bbox["horizontal"].sort(key=lambda x: (-x.y0, x.x0))
            t_bbox["vertical"].sort(key=lambda x: (x.x0, -x.y0))
            self.t_bbox = t_bbox
    
        table = old_generate_table_func(self, table_idx, cols, rows, **kwargs)
    
        if DEBUG:
            _text = []
            _text.extend([(t.x0, t.y0, t.x1, t.y1, t.get_text()) for t in self.horizontal_text])
            _text.extend([(t.x0, t.y0, t.x1, t.y1, t.get_text()) for t in self.vertical_text])
            table._text = _text
            table._t_bbox = self.t_bbox
    
        return table
    
    camelot.parsers.Lattice._generate_table = new_generate_table_func
    camelot_monkeypatched = True


def get_page_soup(url, get_cookies=False, headers={}):
    web_data = requests.get(url, headers=headers)
    if not web_data.ok:
        raise Exception(f"unable to retrieve page {url}")
    soup = BeautifulSoup(web_data.text, 'html.parser')
    if get_cookies:
        cookies = web_data.headers['Set-Cookie']
        cookie = cookies.split(';')[0]
        return soup, cookie
    return soup


def get_links_from_map_page(soup):
    map_s = soup.find('map')
    states = map_s.find_all('area')
    infos = []
    for state in states:
        info = {
            'suburl': state.attrs.get('href', None),
            'title': state.attrs.get('title', None)
        }
        infos.append(info)
    return infos


def get_url(suburl):
    return 'https://www.bbnl.nic.in/{}'.format(suburl)


def get_forward_url(url):
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception(f"unable to retrieve page {url}")

    match = re.search(r"openMe\('(.*)'\);", web_data.text)
    if match is None:
        raise Exception(f'unable to find forward link from {url}')
    return match.group(1)


def ensure_dir(filename):
    Path(filename).parent.mkdir(exist_ok=True, parents= True)


def get_last_updated_date_subpage(soup):
    updated_span = soup.find('span', { 'id': 'lbllastupd' })
    last_updated_date_str = updated_span.text
    last_updated_date = datetime.strptime(last_updated_date_str, "%d/%m/%Y").date()
    return last_updated_date


def combine_files(out_filenames, combined_out_file, enrichers=None):
    logger.info(f'combining into {combined_out_file}')
    with open(combined_out_file, 'w') as out_f:
        wr = csv.writer(out_f)
        wrote_header = False
        for filename in out_filenames:
            if enrichers is not None:
                filename, info = filename
                headers_to_add = list(enrichers.keys())
                fields_to_add = [ info[k].strip() for k in headers_to_add ]
            with open(filename, 'r') as f:
                csv_reader = csv.reader(f)
                row_no = 0
                for row in csv_reader:
                    if row_no == 0:
                        if not wrote_header:
                            if enrichers is not None:
                                row.extend(headers_to_add)
                            wr.writerow(row)
                            wrote_header = True
                    else:
                        if enrichers is not None:
                            row.extend(fields_to_add)
                        wr.writerow(row)
                    row_no += 1


def combine_error_files(errors_filenames, combined_errors_file,
                        key_fn=lambda fname: Path(fname).name.replace('.errors.json', '')):
    errors_filenames = [ x for x in errors_filenames if Path(x).exists() ]
    if len(errors_filenames) == 0:
        return
    logger.info(f'combining into {combined_errors_file}')
    all_errors = {}
    for filename in errors_filenames:
        key = key_fn(filename)
        with open(filename, 'r') as f:
            data = json.load(f)
        all_errors[key] = data
    with open(combined_errors_file, 'w') as f:
        json.dump(all_errors, f, indent=4)


def delete_files(files_to_delete):
    logger.info(f'deleting files: {files_to_delete}')
    for filename in files_to_delete:
        Path(filename).unlink()


def merge_table_data_vertical(data1, data2):
    return data1 + data2
            
def merge_table_data_horizontal(data1, data2):
    if len(data1) != len(data2):
        raise Exception('table length mismatch table1: {}, table2: {}'.format(len(data1), len(data2)))
    merged = []
    for i, row in enumerate(data1):
        out = copy.copy(row)
        out.append('')
        out += data2[i]
        merged.append(out)
    return merged


default_camelot_args = {
    'strip_text':'\n',
    'split_text': True
}


def parse_fn(filename, pno, num_pages,
             page_filename, output_filename,
             flavor_order=[ 'lattice', 'stream' ],
             merge_tables=False,
             discard_overlapping=True,
             camelot_args=default_camelot_args):

    logger.info('processing page {}/{}'.format(pno, num_pages - 1))

    filesize = Path(page_filename).stat().st_size
    output_filename_page = output_filename + f'.{pno}'

    if Path(output_filename_page).exists(): 
        logger.info(f'{output_filename_page} already exists.. skipping')
        return output_filename_page

    logger.info(f'using {page_filename} - {filesize}')
    set_discard_overlapping(discard_overlapping)
    # Try stream when lattice parser fails
    success = False
    for flavor in flavor_order:
        if success:
            break
        logger.info(f'using {flavor} flavor')
        tables = camelot.read_pdf(page_filename,
                                  #backend=ConversionBackend(),
                                  backend='poppler',
                                  pages='1',
                                  flavor=flavor,
                                  **camelot_args)
                                 
        num_tables = len(tables)
        logger.info(f'got {num_tables} tables') 
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

        if merge_tables == False and num_tables != 1:
            logger.warning('has unexpected number of tables')
            continue
        data = []
        for tno, table in enumerate(tables):
            if tno == 0:
                data = table.data
            else:
                if merge_tables == 'v':
                    data = merge_table_data_vertical(data, table.data)
                else:
                    data = merge_table_data_horizontal(data, table.data)
        logger.info(f'got data: {data}')

        success = True

    if not success:
        raise Exception(f'{filename} page {pno} parsing failed')
    
    logger.info(f'writing file {output_filename_page}')
    with open(output_filename_page, 'w') as f:
        csv_writer = csv.writer(f)
        for row in data:
            csv_writer.writerow(row)

    return output_filename_page

def join_pages(output_filename, errors_filename, output_filenames, validator_fn, transform_fn, num_pages):
    logger.info('collating pages')
    pnos = sorted(output_filenames.keys())
    all_data = []
    all_errors = {}
    for pno in pnos:
        filename = output_filenames[pno]
        with open(filename, 'r') as f:
            csv_reader = csv.reader(f)
            row_id = 0
            for row in csv_reader:
                if transform_fn is not None:
                    row = transform_fn(row, row_id, pno, num_pages, all_data)
                    if row == False:
                        row_id += 1
                        continue
                if validator_fn is not None:
                    errors = validator_fn(row)
                    if len(errors) != 0:
                        logger.warning('found validation errors for row - {}: {}'.format(row_id, errors))
                        logger.warning(row)
                        if pno not in all_errors:
                            all_errors[pno] = {}
                        all_errors[pno][row_id] = errors
                all_data.append(row)
                row_id += 1
        
    logger.info(f'writing file {output_filename}')
    with open(output_filename, 'w') as f:
        csv_writer = csv.writer(f)
        for row in all_data:
            csv_writer.writerow(row)

    files_to_delete = output_filenames.values()
    delete_files(files_to_delete)

    if len(all_errors) > 0:
        with open(errors_filename, 'w') as f:
            json.dump(all_errors, f, indent=4)
        return output_filename, errors_filename

    return output_filename, None


# https://stackoverflow.com/a/22726782
class TemporaryDirectory(object):
    def __init__(self, auto_delete=True):
        self.auto_delete = auto_delete
        self.name = None

    def remove(self):
        if self.name is not None:
            shutil.rmtree(self.name)

    def __enter__(self):
        self.name = tempfile.mkdtemp()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.auto_delete:
            self.remove()



def parse_pdf_parallel(executor, filename,
                       validator_fn=None,
                       transform_fn=None,
                       ignore_empty=False,
                       flavor_order=['lattice', 'stream'],
                       merge_tables=False,
                       discard_overlapping=True,
                       camelot_args=default_camelot_args,
                       deferred=False):

    monkeypatch_camelot()

    if deferred:
        f_fut = Future()
        f_fut.set_running_or_notify_cancel()

    def get_result(o_fname, e_fname):
        if deferred:
            f_fut.set_result((o_fname, e_fname))
            return f_fut
        return (o_fname, e_fname)

    with TemporaryDirectory(not deferred) as tempdir:
        logger.info(f'parsing {filename}')
        output_filename = filename.replace('/raw/', '/parsed/')
        output_filename = output_filename.replace('.pdf', '.csv')

        errors_filename = filename.replace('/raw/', '/parsed/')
        errors_filename = errors_filename.replace('.pdf', '.errors.json')
        if Path(output_filename).exists(): 
            logger.info(f'{output_filename} already exists.. skipping')
            if Path(errors_filename).exists():
                return get_result(output_filename, errors_filename)
            else:
                return get_result(output_filename, None)

        ensure_dir(output_filename)
        if ignore_empty and Path(filename).stat().st_size == 0:
            with open(output_filename, 'w'):
                pass
            return get_result(output_filename, None)

        page_map = {}
        output_filenames = {}
        fut_to_pno = {}
        with open(filename, "rb") as f:
            try:
                pdf_reader = PdfFileReader(f, strict=False)
            except Exception as ex:
                if deferred:
                    f_fut.set_exception(ex)
                    return f_fut
                logger.exception(f'{filename} parsing failed')
                raise

            num_pages = pdf_reader.numPages
            for pno in range(num_pages):
                page_map[pno] = pdf_reader.getPage(pno)


            for pno in range(num_pages):
                temp_page_file = Path(tempdir.name).joinpath(f'{random_string(6)}.pdf')
                pdf_writer = PdfFileWriter()
                pdf_writer.addPage(page_map[pno])
                with open(temp_page_file, "wb") as f:
                    pdf_writer.write(f)
                page_filename = f.name

                fut = executor.submit(parse_fn,
                                      filename, pno, num_pages,
                                      page_filename, output_filename,
                                      flavor_order, merge_tables,
                                      discard_overlapping,
                                      camelot_args)
                fut_to_pno[fut] = pno

    
        if deferred:
            def done_cb(fut):
                pno = fut_to_pno[fut]
                try:
                    fname = fut.result()
                except:
                    logger.exception(f'got error for pno: {pno}, filename: {filename}')
                    fname = None
                output_filenames[pno] = fname
                if len(output_filenames) == num_pages:
                    if any([x is None for x in output_filenames.values()]):
                        f_fut.set_exception(Exception('some pages have errors'))
                        return
                    tempdir.remove()
                    f_fut.set_result(join_pages(output_filename, errors_filename, output_filenames, validator_fn, transform_fn, num_pages))

            for fut in fut_to_pno.keys():
                fut.add_done_callback(done_cb)

            return f_fut
        
        done, not_done = wait(fut_to_pno, return_when=ALL_COMPLETED)
        if len(done) != len(fut_to_pno):
            raise Exception('Some pages weren\'t parsed')

        has_errors = False
        for fut in done:
            pno = fut_to_pno[fut]
            try:
                ret = fut.result()
                output_filenames[pno] = ret
            except Exception:
                logger.exception(f'{pno} parsing failed')
                has_errors = True

        if has_errors:
            raise Exception(f'parsing failed for {filename}')

    return join_pages(output_filename, errors_filename, output_filenames, validator_fn, transform_fn, num_pages)
    

def drill_down_and_download(map_info, headers, comp):
    state_url = get_url(map_info['suburl'])
    logger.info('processing state url {}'.format(state_url))
    soup = get_page_soup(state_url, headers=headers)
    state_name = soup.find('span', { 'id': 'lstate' }).text
    state_name = state_name.strip()
    logger.info('processing state {}'.format(state_name))
    view_state = soup.find('input', { 'id': '__VIEWSTATE' }).attrs['value']
    view_state_gen = soup.find('input', { 'id': '__VIEWSTATEGENERATOR' }).attrs['value']
    select = soup.find('select', { 'id': 'ddldist' })
    options = select.find_all('option')
    dist_map = {}
    for option in options:
        value = option.attrs['value']
        name = option.text
        name = name.replace(' District', '')
        if value == '-1':
            continue
        dist_map[name] = value


    form_data = {
        '__EVENTTARGET': 'ddldist',
        '__EVENTARGUMENT': '', 
        '__LASTFOCUS': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_gen,
        '__VIEWSTATEENCRYPTED': '',
        'contrastscheme': '',
        'menu1$txtsearch': '',
    }

    state_map = {}
    for dist_name, value in dist_map.items():
        logger.info('processing district {}'.format(dist_name))
        filename = f'data/raw/{comp}/{state_name}/{dist_name}/blocks.json'
        if Path(filename).exists():
            with open(filename, 'r') as f:
                state_map[dist_name] = json.load(f)
            continue
        form_data['ddldist'] = value
        #TODO: use session instead of requests
        form_headers = {}
        form_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        form_headers.update(headers)
        web_data = requests.post(state_url, data=form_data, headers=form_headers)
        if not web_data.ok:
            raise Exception(f"unable to retrieve dist {dist_name} {comp} page for state {state_name}")
        d_soup = BeautifulSoup(web_data.text, 'html.parser')
        fieldset = d_soup.find('fieldset')
        cols = fieldset.find_all('td')
        block_map = {}
        if len(cols) == 1:
            b = cols[0].find('b')
            if b is not None and b.text == 'No Records Found.':
                cols = []
        for col in cols:
            link = col.find('a')
            block_name = link.attrs['title']
            block_name = block_name.replace(' Block', '')
            block_pdf_url = link.attrs['href']
            block_map[block_name] = block_pdf_url

        ensure_dir(filename)
        with open(filename, 'w') as f:
            json.dump(block_map, f, indent=4)
        state_map[dist_name] = block_map

    for dist_name, block_map in state_map.items():
        for block_name, block_pdf_url in block_map.items():
            logger.info('processing state: {}, dist: {}, block: {}'.format(state_name, dist_name, block_name))
            filename = 'data/raw/{}/{}/{}/{}.pdf'.format(comp, state_name, dist_name, block_name)
            if Path(filename).exists():
                logging.info(f'{filename} exists.. skipping')
                continue
            logger.info(f'getting pdf from {block_pdf_url}')
            web_data = requests.get(block_pdf_url, allow_redirects=False)
            #logger.info(f'status code: {web_data.status_code}, headers: {web_data.headers}')
            if not web_data.ok:
                raise Exception("unable to retrieve block {}, dist {} {} for state {}".format(block_name, dist_name, comp, state_name))

            ensure_dir(filename)
            if web_data.status_code == 302 and web_data.headers['Location'] == 'Noresource.htm':
                logger.info('file not available.. creating empty file')
                with open(filename, 'wb'):
                    pass

            with open(filename, 'wb') as f:
                f.write(web_data.content)



