import io
import csv
import logging
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from lxml import etree
from bs4 import BeautifulSoup
from xlsx2csv import Xlsx2csv

from .ODTReader import ODTTableReader

logger = logging.getLogger(__name__)

def normalize(k):
    return ' '.join(k.split())


def convert_to_dicts(rows, header_row_span=1):
    if header_row_span < 1:
        raise Exception(f'header_row_span {header_row_span} must not be less than 1')

    if len(rows) < header_row_span + 1:
        return []

    def str_joiner(*args):
        return '\n'.join(args)

    header_len = len(rows[0])
    key_rows = rows[:header_row_span]
    key_rows = [ row + max(0, (header_len - len(row))) * [''] for row in key_rows ]
    keys_row = map(str_joiner, *key_rows)
    keys_row = [normalize(k) for k in keys_row]

    dicts = []
    for row in rows[header_row_span:]:
        extra_len = len(keys_row) - len(row)
        row += [''] * extra_len
        d = dict(zip(keys_row, row))
        dicts.append(d)
    return dicts

def records_from_excel(excel_file, header_row_span=1):
    logger.debug('parsing excel file')
    records = []
    ns_map = {}
    in_table = False
    in_row = False
    in_cell = False
    values = []
    data = ''
    NS_NAME = 'ss'

    def fix_tag(tag):
        if NS_NAME not in ns_map:
            return tag
        return '{' + ns_map[NS_NAME] + '}' + tag

    context = ET.iterparse(excel_file, events=('start', 'end', 'start-ns', 'end-ns'))
    for event, elem in context:
        #print(event, elem)
        if event == 'start-ns':
            ns, url = elem
            ns_map[ns] = url
            continue
        if event == 'end-ns':
            continue
        #print(elem, table_tag(ns_map))
        if event == 'start' and elem.tag == fix_tag('Table'):
            #print('starting table')
            in_table = True
            continue
        if event == 'end' and elem.tag == fix_tag('Table'):
            in_table = False
            elem.clear()
            continue
        if not in_table:
            if event == 'end':
                elem.clear()
            continue
        if event == 'start' and elem.tag == fix_tag('Row'):
            in_row = True
            #print('starting row')
            continue
        if event == 'end' and elem.tag == fix_tag('Row'):
            in_row = False
            elem.clear()
            #print("got row: {}".format(values))
            empty = True
            for value in values:
                if value != '':
                    empty = False
                    break
            # process row
            if len(values) > 1 and not empty:
                records.append(values)
            values = []
            continue
        if not in_row:
            if event == 'end':
                elem.clear()
            continue
        if event == 'start' and elem.tag == fix_tag('Cell'):
            #print('starting cell')
            in_cell = True
            continue
        if event == 'end' and elem.tag == fix_tag('Cell'):
            cell_index = int(elem.attrib[fix_tag('Index')]) - 1
            len_to_fill = cell_index - len(values)
            if len_to_fill:
                values.extend([''] * len_to_fill)
            values.append(data)
            data = ''
            elem.clear()
            in_cell = False
            continue
        if not in_cell:
            if event == 'end':
                elem.clear()
            continue
        if event == 'end' and elem.tag == fix_tag('Data'):
            data = elem.text
            elem.clear()
            continue
        if event == 'end':
            elem.clear()
    del context

    dicts = convert_to_dicts(records, header_row_span)
    del records
    return dicts


def records_from_xslx(input_file, header_row_span=0):
    csv_out_file = io.StringIO()
    Xlsx2csv(input_file, outputencoding="utf-8").convert(csv_out_file)
    csv_out_file.seek(0)
    # Skip header rows if specified
    for _ in range(header_row_span):
        next(csv_out_file)
    reader = csv.DictReader(csv_out_file)
    records = [ r for r in reader ]
    nrecs = [{normalize(k):v for k,v in r.items()} for r in records]
    return nrecs


def unzip_single(zipped_content):
    zip_data_file = io.BytesIO(zipped_content)
    with ZipFile(zip_data_file, 'r') as myzip:
        names = myzip.namelist()
        if len(names) != 1:
            raise Exception("unexpected zip format with more than one file")

        with myzip.open(names[0], 'r') as myfile:
            content = myfile.read()
    return names[0], content


def records_from_odt(input_file, drop_tables_front=2, drop_tables_back=0):
    reader = ODTTableReader(input_file, clonespannedcolumns=False)
    logger.debug('got {} tables while converting odt to csv'.format(len(reader.SHEETS)))

    tables = reader.SHEETS[drop_tables_front:]
    logger.debug('dropping front tables: {}'.format(reader.SHEETS[:drop_tables_front]))
    if drop_tables_back != 0:
        tables = tables[:-drop_tables_back]
        logger.debug('dropping back tables: {}'.format(reader.SHEETS[-drop_tables_back:]))
    records = []
    header_taken = False
    for table in tables:
        for i, row in enumerate(table):
            if i == 0 and header_taken:
                continue
            header_taken = True
            records.append(row)

    return convert_to_dicts(records)


def records_from_htm_heavy(input_file):
    out_rows = []
    soup = BeautifulSoup(input_file.read())
    data_table = soup.find('table', { 'id': '__bookmark_2' })
    rows = data_table.find_all('tr')
    for i, row in enumerate(rows):
        tag_name = 'th' if i == 0 else 'td'
        out_cells = []
        cols = row.find_all(tag_name, recursive=False)
        for col in cols:
            data_strs = []
            divs = col.find_all('div', recursive=False)
            for div in divs:
                data_strs.append(str(div.contents[0]))
            out_cells.append('\n'.join(data_strs))
        #pprint(out_cells)
        out_rows.append(out_cells)
        row.decompose()
    return convert_to_dicts(out_rows)


def records_from_htm(html_file, table_id='__bookmark_2', divs_in_cells=True):
    records = []
    in_table = False
    in_row = False
    in_cell = False
    in_div = False
    cell_tag = 'th'
    values = []
    data_strs = []

    def clear(e):
        e.clear()
        for ancestor in e.xpath('ancestor-or-self::*'):
            while ancestor.getprevious() is not None:
                del ancestor.getparent()[0]

    context = etree.iterparse(html_file, events=('start', 'end'), html=True)
    for event, elem in context:
        #print(event, elem.tag)

        if event == 'start' and elem.tag == 'table':
            if 'id' not in elem.attrib or elem.attrib['id'] != table_id:
                continue
            #print('starting table')
            in_table = True
            continue
        if event == 'end' and elem.tag == 'table':
            in_table = False
            cell_tag = 'th'
            clear(elem)
            continue
        if not in_table:
            if event == 'end':
                clear(elem)
            continue

        if event == 'start' and elem.tag == 'tr':
            in_row = True
            #print('starting row')
            continue
        if event == 'end' and elem.tag == 'tr':
            in_row = False
            clear(elem)
            #print("got row: {}".format(values))
            empty = True
            for value in values:
                if value != '':
                    empty = False
                    break
            # process row
            if len(values) > 1 and not empty:
                records.append(values)
            values = []
            if cell_tag == 'th':
                cell_tag = 'td'
            continue
        if not in_row:
            if event == 'end':
                clear(elem)
            continue

        if event == 'start' and elem.tag == cell_tag:
            #print('starting tag: {}'.format(elem.tag))
            in_cell = True
            continue
        if event == 'end' and elem.tag == cell_tag:
            if not divs_in_cells:
                data_strs = [ str(x).strip() for x in elem.itertext() ]
            values.append('\n'.join(data_strs))
            data_strs = []
            clear(elem)
            in_cell = False
            continue
        if not in_cell:
            if event == 'end':
                clear(elem)
            continue

        # don't nest further if we are not expecting data to be in divs inside cells
        if not divs_in_cells and event == 'end':
            clear(elem)
            continue

        if event == 'start' and elem.tag == 'div':
            in_div = True
            continue
        if event == 'end' and elem.tag == 'div':
            #print('div data', elem.attrib, 'text', elem.text, 'iter', list(elem.itertext()))
            if elem.get('style', None) != 'visibility:hidden':
                data_strs.extend([ str(x).strip() for x in elem.itertext() ])
            in_div = False
            clear(elem)
            continue
        if not in_div:
            if event == 'end':
                clear(elem)
            continue

        if elem.tag == 'br':
            continue

        if event == 'end':
            clear(elem)
    del context

    dicts = convert_to_dicts(records) 
    del records
    return dicts


