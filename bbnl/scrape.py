#GS_LIBRARY_PATH = "/opt/homebrew/lib/libgs.dylib"
#import ctypes
#libgs = ctypes.CDLL(GS_LIBRARY_PATH)

import io
import re
import copy
import json
import glob
import os
import os.path
import requests
import csv
import tempfile
import logging
from pathlib import Path
from concurrent.futures import (wait, ALL_COMPLETED,
                                ProcessPoolExecutor)
from datetime import datetime

import camelot
from bs4 import BeautifulSoup
from xlsx2csv import Xlsx2csv
from camelot.utils import (get_page_layout, text_in_bbox,
                           random_string, TemporaryDirectory)
from PyPDF2 import PdfFileReader, PdfFileWriter
from pdfminer.layout import LTRect

#from pikepdf import Pdf, PdfImage, parse_content_stream
#from pdf2image import convert_from_path
#import pdfminer.high_level
#from imgcat import imgcat
#import numpy as np

#import matplotlib
#matplotlib.use("module://imgcat")



logger = logging.getLogger(__name__)

def setup_logging(log_level):
    from colorlog import ColoredFormatter
    formatter = ColoredFormatter("%(log_color)s%(asctime)s [%(levelname)-5s][%(process)d][%(threadName)s] %(message)s",
                                 datefmt='%Y-%m-%d %H:%M:%S',
	                             reset=True,
	                             log_colors={
	                             	'DEBUG':    'cyan',
	                             	'INFO':     'green',
	                             	'WARNING':  'yellow',
	                             	'ERROR':    'red',
	                             	'CRITICAL': 'red',
	                             },
	                             secondary_log_colors={},
	                             style='%')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(level=log_level, handlers=[handler])

    for mod_name in ['pdfminer.pdfinterp', 'pdfminer.pdfpage', 'pdfminer.pdfdocument']:
        _logger = logging.getLogger(mod_name)
        _logger.setLevel(logging.WARNING)



class ConversionBackend(object):
    def convert(self, pdf_path, png_path, resolution=300):
        import ghostscript_alt

        gs_command = [
            "gs",
            "-q",
            "-sDEVICE=png16m",
            "-o",
            png_path,
            f"-r{resolution}",
            pdf_path,
        ]
        gs_call = ' '.join(gs_command)
        gs_call = gs_call.encode().split()
        null = open(os.devnull, "wb")
        with ghostscript_alt.Ghostscript(*gs_call, stdout=null):
            pass
        #with open(png_path) as f:
        #    imgcat(f)
        null.close()


def get_links_from_map_page(url):
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception(f"unable to retrieve page {url}")
    soup = BeautifulSoup(web_data.text, 'html.parser')
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


def get_active_gps(executor):
    state_url_base = 'http://www.bbnl.nic.in/ActiveGps.aspx?state={}'
    for i in range(1,38):
        pdf_file = 'data/raw/activegps/{}.pdf'.format(i)
        if os.path.exists(pdf_file):
            continue
        state_url = state_url_base.format(i)
        web_data = requests.get(state_url)
        if not web_data.ok:
            raise Exception("unable to retrieve main html for state: {}".format(i))
        #soup = BeautifulSoup(web_data.text, 'html.parser')
        #script_code = soup.find('script')
        #print(script_code)
        #window.open('http://www.bbnl.nic.in//WriteReadData/datafiles/J&K_1070a13318e8-992b-495a-abe9-836e0b8cb179.pdf','_self')
        print(web_data.text)
        match = re.match(r"<script>window.open\('(.*)','_self'\)</script>", web_data.text)
        if match is None:
            if web_data.text.find("<script>alert('Data Not Available');location.href='actgps.aspx'</script>") == -1:
                raise Exception('Unexpected format of pdf url for state: {}'.format(i))
            else:
                with open(pdf_file, 'w') as f:
                    continue
        pdf_url = match.group(1)
        print(pdf_url)
        web_data = requests.get(pdf_url)
        if not web_data.ok:
            raise Exception("unable to retrieve list pdf for state: {}".format(i))
        print(web_data.headers)
        with open(pdf_file, 'wb') as f:
            f.write(web_data.content)


def validate_active_gp(row):
    if all([ x == '' for x in row]):
        return []
    non_empty = [0, 1, 2, 3, 4]
    errors = []
    for colno in non_empty:
        if row[colno] == '':
            errors.append('col {} not expected to be empty'.format(colno))
    return errors


def parse_active_gps(executor):
    filenames = glob.glob('data/raw/activegps/*.pdf')
    for filename in filenames:
        csv_file = filename.replace('.pdf', '.csv')
        errors_file = filename.replace('.pdf', '.errors.json')
        errors_all = {}
        print('processing file: {}'.format(filename))
        if os.stat(filename).st_size == 0:
            if os.path.exists(csv_file):
                continue
            print('empty pdf file.. shortcircuiting')
            with open(csv_file, 'w') as f:
                pass
            continue

        if os.path.exists(csv_file):
            continue

        with open(filename, "rb") as pdf_file:
            pdf_reader = PdfFileReader(pdf_file, strict=False)
            num_pages = pdf_reader.numPages

        all_data = []
        for pno in range(num_pages):
            print('processing page {}'.format(pno))
            tables = camelot.read_pdf(filename, backend=ConversionBackend(), pages='{}'.format(pno + 1))
            table = tables[0]
            #plt = camelot.plot(table, kind='grid')
            #plt.show()
            #print(table.data)
            data = copy.copy(table.data)
            expected_len = 5
            if pno == 0:
                expected_len = 6
                # drop the table header
                data = data[1:]

            filt_data = []
            for rowid, row in enumerate(data):
                if len(row) != expected_len:
                    print('unexpected number of cols: {} in row: {}, pno: {}'.format(len(row), rowid, pno))
                    print(row)
                    if len(row) < expected_len:
                        row += [''] * (expected_len - len(row))
                filt_data.append(row[:5])
                errors = validate_active_gp(row)
                if len(errors) != 0:
                    print('found validation errors for row - {}: {}'.format(rowid, errors))
                    print(row)
                    errors_all[pno] = errors
            data = filt_data
            all_data += data

        with open(csv_file, 'w') as f:
            csv_writer = csv.writer(f, delimiter=';')
            for row in all_data:
                csv_writer.writerow(row)
        
        if len(errors_all) > 0:
            with open(errors_file, 'w') as f:
                json.dump(errors_all, f, indent=4)




def get_blocks_connected_gps(exxecutor):
    url = 'http://www.bbnl.nic.in/WriteReadData/LINKS/List_GPs_Fbr_Blck6253a7e4-366d-41ac-89fc-9fd94d047763.pdf'
    pdf_file = 'data/raw/block_connected_gps.pdf'
    if os.path.exists(pdf_file):
        return
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception("unable to retrieve block connected gps")
    with open(pdf_file, 'wb') as f:
        f.write(web_data.content)

def validate_blocks_connected_gps(row):
    if all([ x == '' for x in row]):
        return []
    errors = []
    non_empty = [ 0, 1, 2, 3, 4 ]
    for colid in non_empty:
        if row[colid] == '':
            errors.append(f'col {colid} is empty')
    return errors


def parse_blocks_connected_gps(executor):
    pdf_file = 'data/raw/block_connected_gps.pdf'
    csv_file = 'data/raw/block_connected_gps.csv'
    errors_file = 'data/raw/block_connected_gps.errors.json'
    if os.path.exists(csv_file):
        return

    with open(pdf_file, "rb") as f:
        pdf_reader = PdfFileReader(f, strict=False)
        num_pages = pdf_reader.numPages

    all_data = []
    for pno in range(num_pages):
        logger.info('processing page {}'.format(pno))
        errors_all = {}
        tables = camelot.read_pdf(pdf_file,
                                  backend=ConversionBackend(),
                                  pages='{}'.format(pno + 1))
        table = tables[0]
        data = copy.copy(table.data)
        if pno == 0:
            data = data[1:]

        expected_len = 5
        filt_data = []
        for rowid, row in enumerate(data):
            if len(row) != expected_len:
                print('unexpected number of cols: {} in row: {}, pno: {}'.format(len(row), rowid, pno))
                print(row)
                if len(row) < expected_len:
                    row += [''] * (expected_len - len(row))
            filt_data.append(row[:expected_len])
            errors = validate_blocks_connected_gps(row)
            if len(errors) != 0:
                print('found validation errors for row - {}: {}'.format(rowid, errors))
                print(row)
                errors_all[pno] = errors
        all_data += data

    with open(csv_file, 'w') as f:
        csv_writer = csv.writer(f, delimiter=';')
        for row in all_data:
            csv_writer.writerow(row)

    if len(errors_all) > 0:
        with open(errors_file, 'w') as f:
            json.dump(errors_all, f, indent=4)

        
def get_block_graphs(executor):
    main_url = 'http://www.bbnl.nic.in/index.aspx'
    web_data = requests.get(main_url)
    if not web_data.ok:
        raise Exception("unable to retrieve main bbnl page")
    cookies = web_data.headers['Set-Cookie']
    cookie = cookies.split(';')[0]
    headers = {
        'Cookie': cookie
    }

    state_url_base = 'http://www.bbnl.nic.in/fiberdata.aspx?state={}'
    for i in range(1,38):
        web_data = requests.get(state_url_base.format(i), headers=headers)
        if not web_data.ok:
            raise Exception("unable to retrieve state {} fiberdata main page".format(i))
        soup = BeautifulSoup(web_data.text, 'html.parser')
        state_name = soup.find('span', { 'id': 'lstate' }).text
        state_name = state_name.strip()
        print('processing state {}'.format(state_name))
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
            print('processing district {}'.format(dist_name))
            filename = 'data/raw/block_graphs/{}/{}/blocks.json'.format(state_name, dist_name)
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    state_map[dist_name] = json.load(f)
                continue
            form_data['ddldist'] = value
            form_headers = copy.copy(headers)
            form_headers['Content-Type'] = 'application/x-www-form-urlencoded'
            web_data = requests.post(state_url_base.format(i), data=form_data, headers=form_headers)
            if not web_data.ok:
                raise Exception("unable to retrieve dist {} fiberdata page for state {}".format(dist_name, i))
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

            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(block_map, f, indent=4)
            state_map[dist_name] = block_map

        for dist_name, block_map in state_map.items():
            for block_name, block_pdf_url in block_map.items():
                print('processing state: {}, dist: {}, block: {}'.format(state_name, dist_name, block_name))
                filename = 'data/raw/block_graphs/{}/{}/{}.pdf'.format(state_name, dist_name, block_name)
                if os.path.exists(filename):
                    continue
                web_data = requests.get(block_pdf_url)
                if not web_data.ok:
                    raise Exception("unable to retrieve block {}, dist {} fiberdata page for state {}".format(block_name, dist_name, i))
                dirname = os.path.dirname(filename)
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
                with open(filename, 'wb') as f:
                    f.write(web_data.content)

        


def get_implementers(executor):
    print('processing india page')
    url = 'http://www.bbnl.nic.in/index1.aspx?lsid=479&lev=2&lid=392&langid=1'
    #url = 'http://www.bbnl.nic.in/statewise.aspx?langid=1'
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception("unable to retrieve implementers main page")
    soup = BeautifulSoup(web_data.text, 'html.parser')
    map_s = soup.find('map')
    states = map_s.find_all('area')
    dirname = 'data/raw/implementers/'
    os.makedirs(dirname, exist_ok=True)
    for state in states:
        suburl = state.attrs['href']
        filename = suburl.split('/')[-1]
        if filename in ['4.pdf', '23.pdf', '24.pdf', '#']: 
            continue
        full_filename = dirname + filename
        if os.path.exists(full_filename):
            continue
        print(f'processing page: {filename}')
        state_url = f'http://www.bbnl.nic.in/{suburl}'
        web_data = requests.get(state_url)
        if not web_data.ok:
            raise Exception(f"unable to retrieve implementers page at {suburl}")
        if web_data.headers['Content-Type'] != 'application/pdf':
            print(web_data.headers['Content-Type'])
            #print(web_data.text)
            continue
            #raise Exception(f"unexpected content type when retrieving implementers page at {suburl}")

        with open(full_filename, 'wb') as f:
            f.write(web_data.content)

def parse_implementers(executor):
    filenames = glob.glob('data/raw/implementers/*.pdf')
    all_data = []
    for filename in filenames:
        with open(filename, "rb") as pdf_file:
            pdf_reader = PdfFileReader(pdf_file, strict=False)
            num_pages = pdf_reader.numPages

        for pno in range(num_pages):
            print('processing page {}'.format(pno))
            tables = camelot.read_pdf(filename,
                                      backend=ConversionBackend(),
                                      pages='{}'.format(pno + 1),
                                      flavor='lattice',
                                      strip_text='\n',
                                      #discard_overlapping=False,
                                      split_text=True)
            table = tables[0]
            data = copy.copy(table.data)
            data = [ row for row in data if not all([ x == '' for x in row]) ]
            print(data)
            header = data[0][1]
            header_parts = header.split(' ')
            phase = header_parts[0]
            state_name = ' '.join(header_parts[1:])
            data_map = {
                'state_name': state_name,
                'phase': phase
            }
            data = data[1:]
            for row in data: 
                key = row[3]
                value = row[5]
                data_map[key] = value
            all_data.append(data_map)

    with open('data/raw/implementers/all.csv', 'w') as f:
        writer = csv.DictWriter(f, fieldnames=list(all_data[0].keys()), delimiter=';')
        writer.writeheader()
        for entry in all_data:
            writer.writerow(entry)

   



def get_locations(executor):
    # from Navigation
    #url = 'http://www.bbnl.nic.in/index1.aspx?langid=1&lev=2&lsid=655&pid=2&lid=526'
    # from New Ticker
    url = 'http://www.bbnl.nic.in/index1.aspx?lsid=652&lev=2&lid=526&langid=1'
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception("unable to retrieve locations main page")
    soup = BeautifulSoup(web_data.text, 'html.parser')
    div = soup.find('div', { 'id': "maincontaint_main_display" })
    table = div.find('table', { 'class': "MsoTableGrid" })
    rows = table.find_all('tr')

    state_info = {}
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
        state_info[state_name] = {
            "FPOIs": url1,
            "OLTs": url2
        }
    print(state_info)

    def get_page(p_url, csv_file_name):
        print('writing {} to {}'.format(p_url, csv_file_name))
        if os.path.exists(csv_file_name):
            return
        web_data = requests.get(p_url)
        if not web_data.ok:
            raise Exception("unable to retrieve locations state page")

        dirname = os.path.dirname(csv_file_name)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if web_data.headers['Content-Type'] == 'application/pdf; charset=utf-8':
            with open(csv_file_name.replace('.csv', '.pdf'), 'wb') as f:
                print('writing pdf instead')
                #print(web_data.content)
                f.write(web_data.content)
            return

        data_file = io.BytesIO(web_data.content)
        Xlsx2csv(data_file, outputencoding="utf-8", delimiter=';').convert(csv_file_name)

    for state_name, info in state_info.items():
        if info['FPOIs'] is not None:
            get_page(info['FPOIs'], 'raw/locations/{}/FPOIs.csv'.format(state_name))
        if info['OLTs'] is not None:
            get_page(info['OLTs'], 'raw/locations/{}/OLTs.csv'.format(state_name))

def validate_olt_row(row):
    if all([ x == '' for x in row]):
        return []
    errors = []
    for colno, col in enumerate(row):
        if col == '':
            errors.append('col {} not expected to be empty'.format(colno))
    return errors

def validate_fpoi_row(row):
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


def validate_fpoi_row_fix(row):
    non_empty_cols = [0, 1, 2, 3, 4, 5]
    empty_cols = [6]
    non_empty_together = [7, 8, 9]

    if all([ x == '' for x in row]):
        return [], row

    errors = []
    fixed_row = copy.copy(row)
    for colno in non_empty_cols:
        if row[colno] == '':
            if colno > 0:
                prev_lines = row[colno - 1].split('\n')
                if len(prev_lines) > 1 and prev_lines[-1].strip() != '':
                    fixed_row[colno - 1] = '\n'.join(prev_lines[:-1])
                    fixed_row[colno] = prev_lines[-1].strip()
                    print('copying line {} col from {} to {}'.format(fixed_row[colno], colno - 1, colno))
                    continue
            errors.append('col {} not expected to be empty'.format(colno))
    for colno in empty_cols:
        if row[colno] != '':
            errors.append('col {} expected to be empty but has "{}"'.format(colno, row[colno]))

    non_empty_together_cols = [ row[x] for x in non_empty_together ]
    non_empty_together_cols_check = [ x == '' for x in non_empty_together_cols ]
    if not all(non_empty_together_cols_check) and any(non_empty_together_cols_check):
        correction_count = 0
        for colno in non_empty_together:
            if row[colno] == '':
                prev_lines = row[colno - 1].split('\n')
                if len(prev_lines) > 1 and prev_lines[-1].strip() != '':
                    correction_count += 1
                    fixed_row[colno - 1] = '\n'.join(prev_lines[:-1])
                    fixed_row[colno] = prev_lines[-1].strip()
                    print('copying line {} col from {} to {}'.format(fixed_row[colno], colno - 1, colno))
        if len(non_empty_together_cols) != correction_count:
            errors.append('cols {} expected to be empty together {}'.format(non_empty_together, non_empty_together_cols))
    return errors, fixed_row

            
def merge_table_data(data1, data2):
    if len(data1) != len(data2):
        raise Exception('table length mismatch table1: {}, table2: {}'.format(len(data1), len(data2)))
    merged = []
    for i, row in enumerate(data1):
        out = copy.copy(row)
        out.append('')
        out += data2[i]
        merged.append(out)
    return merged


def parse_FPOIs(executor):
    filenames = glob.glob('data/raw/locations/*/FPOIs.pdf')
    #filenames = [ 'data/raw/locations/Jammu & Kashmir/FPOIs.pdf' ]
    for filename in filenames:
        print('processing file: {}'.format(filename))

        if filename in ['data/raw/locations/Assam/FPOIs.pdf','data/raw/locations/Karnataka/FPOIs.pdf']:
            print(f'skipping {filename} because of known problems')
            continue

        csv_file_name = filename.replace('.pdf', '.csv')
        errors_file_name = filename.replace('.pdf', '.errors.json')
        if os.path.exists(csv_file_name):
            continue
        with open(filename, "rb") as pdf_file:
            pdf_reader = PdfFileReader(pdf_file, strict=False)
            num_pages = pdf_reader.numPages
        all_data = []
        all_errors = {}

        def debug_table(table):
            plt = camelot.plot(table, kind='grid')
            plt.show()
            plt = camelot.plot(table, kind='text')
            plt.show()
            for rowid, row in enumerate(table.cells):
                print(f'processing row {rowid}')
                for colid, cell in enumerate(row):
                    print('col at {} with vspan: {}, hspan: {}, left: {}, right: {}, top: {}, bottom: {}, text: {}'.format(
                        cell, cell.vspan, cell.hspan, cell.left, cell.right, cell.top, cell.bottom, cell._text))

            for s in table._text_full:
                print(s)

        for pno in range(num_pages):
            print('processing page {}'.format(pno))
            #laparams = {
            #    #'line_overlap': 1.0,
            #    #'char_margin': 1.0,
            #    #'line_margin': 0.4,
            #    #'boxes_flow': 0.0,
            #}
            tables = camelot.read_pdf(filename,
                                      backend=ConversionBackend(),
                                      pages='{}'.format(pno + 1),
                                      flavor='lattice',
                                      #layout_kwargs=laparams,
                                      discard_overlapping=False,
                                      split_text=True)
            table = tables[0]
            if pno != 0:
                if len(tables) > 2:
                    raise Exception('unexpected number of tables: {}'.format(len(tables)))
                if len(tables) == 2:
                    data = merge_table_data(copy.copy(tables[0].data), copy.copy(tables[1].data))
                else:
                    data = copy.copy(table.data)
            else:
                if len(tables) != 1:
                    raise Exception('unexpected number of tables: {}'.format(len(tables)))
                data = copy.copy(table.data)
            if pno == 0:
                data = data[1:]
                if 'GP_DETAILS' in data[0]:
                    data = data[1:]

            expected_len = 10
            filt_data = []
            for rowid, row in enumerate(data):
                if len(row) != expected_len:
                    print('unexpected number of cols: {} in row: {}, pno: {}'.format(len(row), rowid, pno))
                    print(row)
                    if len(row) < expected_len:
                        row += [''] * (expected_len - len(row))
                errors, fixed_row = validate_fpoi_row_fix(row)
                if len(errors) != 0:
                    print('found validation errors on row: {}: {}'.format(rowid, errors))
                    print(row)
                    #print(data_without_split[rowid])
                    if pno not in all_errors:
                        all_errors[pno] = {}
                    all_errors[pno][rowid] = errors
                row = fixed_row
                filt_data.append(row[:expected_len])
            if pno in all_errors:
                debug_table(table)
            all_data += filt_data

        with open(csv_file_name, 'w') as f:
            csv_writer = csv.writer(f, delimiter=';')
            for row in all_data:
                csv_writer.writerow(row)

        if len(all_errors) > 0:
            with open(errors_file_name, 'w') as f:
                json.dump(all_errors, f, indent=4)
 
def parse_OLTs(executor):
    filenames = glob.glob('data/raw/locations/*/OLTs.pdf')
    for filename in filenames:
        print('processing file: {}'.format(filename))

        csv_file_name = filename.replace('.pdf', '.csv')
        errors_file_name = filename.replace('.pdf', '.errors.json')
        if os.path.exists(csv_file_name):
            continue
        with open(filename, "rb") as pdf_file:
            pdf_reader = PdfFileReader(pdf_file, strict=False)
            num_pages = pdf_reader.numPages

        
        all_data = []
        all_errors = {}
        for pno in range(num_pages):
            print('processing page {}'.format(pno))
            laparams = {
                #'line_overlap': 0.8,
                'char_margin': 1.0,
                #'line_margin': 0.4,
                #'boxes_flow': None,
            }
            tables = camelot.read_pdf(filename, backend=ConversionBackend(), pages='{}'.format(pno + 1), flavor='lattice', layout_kwargs=laparams, split_text=True)
            table = tables[0]
            #plt = camelot.plot(table, kind='contour')
            #plt.show()
            if len(tables) != 1:
                raise Exception('unexpected number of tables: {}'.format(len(tables)))
            data = copy.copy(table.data)
            #print(data)
            if pno == 0:
                data = data[1:]

            expected_len = 6

            filt_data = []
            for rowid, row in enumerate(data):
                if len(row) != expected_len:
                    print('unexpected number of cols: {} in row: {}, pno: {}'.format(len(row), rowid, pno))
                    print(row)
                    if len(row) < expected_len:
                        row += [''] * (expected_len - len(row))
                errors = validate_olt_row(row)
                if len(errors) != 0:
                    print('found validation errors for row - {}: {}'.format(rowid, errors))
                    print(row)
                    all_errors[pno] = errors

                filt_data.append(row[:expected_len])
            all_data += data

        with open(csv_file_name, 'w') as f:
            csv_writer = csv.writer(f, delimiter=';')
            for row in all_data:
                csv_writer.writerow(row)

        if len(all_errors) > 0:
            with open(errors_file_name, 'w') as f:
                json.dump(all_errors, f, indent=4)


def parse_locations(executor):
    parse_OLTs(executor)
    parse_FPOIs(executor)


#from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
#from pdfminer.pdfpage import PDFPage
#from pdfminer.converter import PDFLayoutAnalyzer
#from pdfminer.high_level import extract_text_to_fp

#from pdf2image import convert_from_path
#import cv2
#from PIL import Image

#def show_grayscale(cv_img):
#    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2BGR)
#    p_img = Image.fromarray(cv_img)
#    imgcat(p_img)


def parse_block_graphs(executor):
    pass
    #filenames = glob.glob('data/raw/block_graphs/*/*/*.pdf')
    #for filename in filenames:
    #    print('processing {}'.format(filename))
    #    images = convert_from_path(filename)
    #    print('found {} images'.format(len(images)))
    #    for image in images:
    #        # find all text
    #        # detect and remove it.. but keep coordinates
    #        image = image.convert('RGB')
    #        image = np.array(image)
    #        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    #        #original = image
    #        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #        ret, thresh1 = cv2.threshold(image, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
    #        show_grayscale(thresh1)
    #        rect_size = 5
    #        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (rect_size, rect_size))
    #        dilation = cv2.dilate(thresh1, rect_kernel, iterations = 1)
    #        show_grayscale(dilation)
    #        contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    #        #show_grayscale(contours)



    #        #show_grayscale(image)
    #        #edges = cv2.Canny(image, 30, 100)
    #        #show_grayscale(edges)

    #        #cv2.imshow("edges", edges)
    #        #imgcat(image)
    #        #exit()



#TODO: get last update times

def get_status_active_gps(executor):
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
    header_color = (1.0, 1.0, 0.0)
    for rect in first_row_rects:
        if rect.non_stroking_color == header_color:
            is_header = True
            break
    return is_header

def get_status_active_gps_page(filename, pno, num_pages, page_filename, output_filename):
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
                                  backend=ConversionBackend(),
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
        csv_writer = csv.writer(f, delimiter=';')
        for row in data:
            csv_writer.writerow(row)
    return ret


def parse_status_active_gps(executor):
    filenames = glob.glob('data/raw/active_gp_status/*.pdf')
    #filenames = [ 'data/raw/active_gp_status/ANDHRA PRADESH.pdf' ]

    with TemporaryDirectory() as tempdir:
        for filename in filenames:
            logger.info(f'parsing {filename}')

            output_filename = filename.replace('/raw/', '/parsed/')
            output_filename = output_filename.replace('.pdf', '.csv')
            if Path(output_filename).exists(): 
                logger.info(f'{output_filename} already exists.. skipping')
                continue

            directory = Path(output_filename).parent
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)

            errors_filename = filename.replace('/raw/', '/parsed/')
            errors_filename = errors_filename.replace('.pdf', '.errors.json')

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

                    fut = executor.submit(get_status_active_gps_page,
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
                    csv_reader = csv.reader(f, delimiter=';')
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
                csv_writer = csv.writer(f, delimiter=';')
                for row in all_data:
                    csv_writer.writerow(row)

            files_to_delete = list(output_filenames.values()) + list(has_header_filenames.values())
            logger.info(f'deleting files: {files_to_delete}')
            for filename in files_to_delete:
                Path(filename).unlink()


def get_panchayats(executor):
    pass
        
def parse_panchayats(executor):
    pass


comp_map = {
    'active_gps': {
        'desc': 'All Service Ready Gram Panchayats',
        'location': 'Home --> Services --> List Of Service Ready GP',
        'scrape': get_active_gps,
        'parse': parse_active_gps
    },
    'status_active_gps': {
        'desc': 'Status Of Active Gram Panchayats',
        'location': 'Home --> Services --> Status Of GPs',
        'scrape': get_status_active_gps,
        'parse': parse_status_active_gps
    },
    'block_connected_gps': {
        'desc': 'List of Gram Panchayats where fiber of BBNL is available up to the Blocks from the GPs',
        'location': 'Home --> Services --> List of Gram Panchayats where fiber of BBNL is available up to the Blocks from the GPs',
        'scrape': get_blocks_connected_gps,
        'parse': parse_blocks_connected_gps
    },
    'block_graphs': {
        'desc': 'Block wise line diagrams for BharatNet and BBNL dark fiber',
        'location': 'Home --> Services -> Block wise line diagrams for BharatNet and BBNL dark fiber',
        'scrape': get_block_graphs,
        'parse': parse_block_graphs
    },
    'locations': {
        'desc': 'Lat-Long of GPs, FPOIs and OLTs for GPs under BharatNet Phase-I',
        #'location': 'Navigation --> Lat-Long of GPs, FPOIs and OLTs for GPs under BharatNet Phase-I',
        'location': 'Home --> New Ticker --> Lat-Long of GPs, FPOIs and OLTs for GPs under BharatNet Phase-I',
        'scrape': get_locations,
        'parse': parse_locations
    },
    'implementers': {
        'desc': 'State Wise Details (Phase 1)',
        'location': 'Home --> Projects --> State Wise Details (Phase 1)',
        'scrape': get_implementers,
        'parse': parse_implementers
    },
    'panchayats': {
        'desc': 'Panchayat Ids',
        'location': 'Home -> Know your Panchayats',
        'scrape': get_panchayats,
        'parse': parse_panchayats
    }
}

def run(action, comp, executor):
    func = comp_map[comp][action]
    func(executor)

def get_last_updated_date(soup):
    bottom_div = soup.find('div', { 'id': "bottom" })
    visitor_panel = bottom_div.find('div', { 'class': 'visitor_panel' })
    updated_span = visitor_panel.find('span', { 'id': 'bottom_last' })
    last_updated_date_str = updated_span.text
    last_updated_date_str = last_updated_date_str.replace('Last Updated On:', '').strip()
    last_updated_date = datetime.strptime(last_updated_date_str, "%d/%m/%Y").date()
    return last_updated_date

def parse_main_page():
    url = 'http://www.bbnl.nic.in'
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception("unable to retrieve main page")
    soup = BeautifulSoup(web_data.text, 'html.parser')
    return soup


if __name__ == '__main__':
    import argparse


    all_comp_names = comp_map.keys()
    all_actions = ['scrape', 'parse']

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--comp', help=f'component to work on, should be one of {all_comp_names}', action='extend', nargs='+', type=str, default=[])
    parser.add_argument('-n', '--no-comp', help=f'component to skip, should be one of {all_comp_names}', action='extend', nargs='+', type=str, default=[])
    parser.add_argument('-a', '--action',  help=f'action to execute, one of {all_actions}', action='extend', nargs='+', type=str, default=[])
    parser.add_argument('-p', '--num-parallel', help='number of parallel processes to use', type=int, default=1)
    parser.add_argument('-l', '--log-level', help='Set the logging level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], type=str, default='DEBUG')
    args = parser.parse_args()

    setup_logging(args.log_level)

    all_comp_names = set(all_comp_names)
    comps_to_run = set(args.comp)
    comps_to_not_run = set(args.no_comp)
    if len(comps_to_run) and len(comps_to_not_run):
        raise Exception("Can't specify bot comps to tun and not run")
    if len(comps_to_not_run) == 0:
        if len(comps_to_run) == 0:
            comps_to_run = all_comp_names
        unknown_comps = comps_to_run - all_comp_names
        if len(unknown_comps) != 0:
            raise Exception('Unknown components specified: {}'.format(unknown_comps))
    else:
        unknown_comps = comps_to_not_run - all_comp_names
        if len(unknown_comps) != 0:
            raise Exception('Unknown components specified: {}'.format(unknown_comps))
        comps_to_run = all_comp_names - comps_to_not_run

    actions_to_run = set(args.action)
    if len(actions_to_run) == 0:
        actions_to_run = set(all_actions)

    unknown_actions = actions_to_run - set(all_actions)
    if len(unknown_actions):
        raise Exception(f'unknown actions {unknown_actions} specified')

    if 'scrape' in actions_to_run:
        soup = parse_main_page()
        last_updated_date = get_last_updated_date(soup)
        logger.info(f'last updated date on the site is {last_updated_date}')
        menus = soup.find_all('a', {'class': 'menuanchor'})

    exit()

    with ProcessPoolExecutor(max_workers=args.num_parallel) as executor:
        for action in all_actions:
            if action in actions_to_run:
                for comp in comps_to_run:
                    run(action, comp, executor)


    

