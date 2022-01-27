import io
import csv
import logging
import xml.etree.ElementTree as ET
import odf.opendocument

from lxml import etree
from bs4 import BeautifulSoup
from zipfile import ZipFile
from xlsx2csv import Xlsx2csv
from odf.table import Table, TableRow, TableCell
from odf.text import P

logger = logging.getLogger(__name__)

def normalize(k):
    return ' '.join(k.split())


def convert_to_dicts(rows, header_row_span=1):
    if len(rows) < header_row_span + 1:
        return []

    def str_joiner(*args):
        return '\n'.join(args)

    key_rows = rows[:header_row_span]
    logger.debug(rows[:4])
    keys_row = map(str_joiner, *key_rows)
    keys_row = [normalize(k) for k in keys_row]
    logger.debug(keys_row)

    dicts = []
    for row in rows[header_row_span:]:
        extra_len = len(keys_row) - len(row)
        row += [''] * extra_len
        d = dict(zip(keys_row, row))
        dicts.append(d)
    return dicts


def fix_tag(ns, tag, nsmap):
    if ns not in nsmap:
        return tag
    return '{' + nsmap[ns] + '}' + tag

def table_tag(ns_map):
    return fix_tag('ss', 'Table', ns_map)

def row_tag(ns_map):
    return fix_tag('ss', 'Row', ns_map)

def cell_tag(ns_map):
    return fix_tag('ss', 'Cell', ns_map)

def data_tag(ns_map):
    return fix_tag('ss', 'Data', ns_map)

def index_tag(ns_map):
    return fix_tag('ss', 'Index', ns_map)

def records_from_excel(excel_file, header_row_span=1):
    logger.debug('parsing excel file')
    records = []
    ns_map = {}
    in_table = False
    in_row = False
    in_cell = False
    values = []
    data = ''
    for event, elem in ET.iterparse(excel_file, events=('start', 'end', 'start-ns', 'end-ns')):
        #print(event, elem)
        if event == 'start-ns':
            ns, url = elem
            ns_map[ns] = url
            continue
        if event == 'end-ns':
            continue
        #print(elem, table_tag(ns_map))
        if event == 'start' and elem.tag == table_tag(ns_map):
            #print('starting table')
            in_table = True
            continue
        if event == 'end' and elem.tag == table_tag(ns_map):
            in_table = False
            elem.clear()
            continue
        if not in_table:
            if event == 'end':
                elem.clear()
            continue
        if event == 'start' and elem.tag == row_tag(ns_map):
            in_row = True
            #print('starting row')
            continue
        if event == 'end' and elem.tag == row_tag(ns_map):
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
        if event == 'start' and elem.tag == cell_tag(ns_map):
            #print('starting cell')
            in_cell = True
            continue
        if event == 'end' and elem.tag == cell_tag(ns_map):
            cell_index = int(elem.attrib[index_tag(ns_map)]) - 1
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
        if event == 'end' and elem.tag == data_tag(ns_map):
            data = elem.text
            elem.clear()
            continue
        if event == 'end':
            elem.clear()
    return convert_to_dicts(records, header_row_span)




# http://stackoverflow.com/a/4544699/1846474
class GrowingList(list):
    def __setitem__(self, index, value):
        if index >= len(self):
            self.extend([None]*(index + 1 - len(self)))
        list.__setitem__(self, index, value)

# from https://github.com/marcoconti83/read-ods-with-odfpy modified for ODT Table reading
class ODTTableReader:
    # loads the file
    def __init__(self, file, clonespannedcolumns=None):
        self.clonespannedcolumns = clonespannedcolumns
        self.doc = odf.opendocument.load(file)
        start_node = self.doc.text
        self.SHEETS = []
        for sheet in start_node.getElementsByType(Table):
            if sheet.parentNode != start_node:
                continue
            self.readSheet(sheet)

    # reads a sheet in the sheet dictionary, storing each sheet as an
    # array (rows) of arrays (columns)
    def readSheet(self, sheet):
        #name = sheet.getAttribute("name")
        rows = sheet.getElementsByType(TableRow)
        arrRows = []

        # for each row
        for row in rows:
            if row.parentNode != sheet and row.parentNode.parentNode != sheet:
                continue
            row_comment = ""
            arrCells = GrowingList()
            cells = row.getElementsByType(TableCell)

            # for each cell
            count = 0
            for cell in cells:
                if cell.parentNode != row and cell.parentNode.parentNode != row:
                    continue
                # repeated value?
                repeat = cell.getAttribute("numbercolumnsrepeated")
                if not repeat:
                    repeat = 1
                    spanned = int(cell.getAttribute('numbercolumnsspanned') or 0)
                    # clone spanned cells
                    if self.clonespannedcolumns is not None and spanned > 1:
                        repeat = spanned

                ps = cell.getElementsByType(P)
                textContent = ""

                # for each text/text:span node
                for p in ps:
                    for n in p.childNodes:
                        if (n.nodeType == 1 and n.tagName == "text:span"):
                            for c in n.childNodes:
                                #print('{}/{} c: type: {}, {}'.format(rowid, cellid, c.nodeType, c.tagName))
                                if (c.nodeType == 3):
                                    textContent = u'{}{}'.format(textContent, c.data)

                        if (n.nodeType == 3):
                            textContent = u'{}{}'.format(textContent, n.data)

                if(textContent):
                    if(textContent[0] != "#"):  # ignore comments cells
                        for rr in range(int(repeat)):  # repeated?
                            arrCells[count]=textContent
                            count+=1
                    else:
                        row_comment = row_comment + textContent + " "
                else:
                    for rr in range(int(repeat)):
                        count+=1

            # if row contained something
            if(len(arrCells)):
                arrRows.append(arrCells)

            #else:
            #    print ("Empty or commented row (", row_comment, ")")

        self.SHEETS.append(arrRows)

    # returns a sheet as an array (rows) of arrays (columns)
    def getSheet(self, name):
        return self.SHEETS[name]



def records_from_xslx(input_file):
    csv_out_file = io.StringIO()
    Xlsx2csv(input_file, outputencoding="utf-8", delimiter=';').convert(csv_out_file)
    csv_out_file.seek(0)
    reader = csv.DictReader(csv_out_file, delimiter=';')
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


def records_from_htm(html_file):
    records = []
    in_table = False
    in_row = False
    in_cell = False
    in_div = False
    cell_tag = 'th'
    values = []
    data_strs = []
    for event, elem in etree.iterparse(html_file, events=('start', 'end'), html=True):
        #print(event, elem.tag)

        if event == 'start' and elem.tag == 'table':
            if 'id' not in elem.attrib or elem.attrib['id'] != '__bookmark_2':
                continue
            #print('starting table')
            in_table = True
            continue
        if event == 'end' and elem.tag == 'table':
            in_table = False
            cell_tag = 'th'
            elem.clear()
            continue
        if not in_table:
            if event == 'end':
                elem.clear()
            continue

        if event == 'start' and elem.tag == 'tr':
            in_row = True
            #print('starting row')
            continue
        if event == 'end' and elem.tag == 'tr':
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
            if cell_tag == 'th':
                cell_tag = 'td'
            continue
        if not in_row:
            if event == 'end':
                elem.clear()
            continue

        if event == 'start' and elem.tag == cell_tag:
            #print('starting tag: {}'.format(elem.tag))
            in_cell = True
            continue
        if event == 'end' and elem.tag == cell_tag:
            values.append('\n'.join(data_strs))
            data_strs = []
            elem.clear()
            in_cell = False
            continue
        if not in_cell:
            if event == 'end':
                elem.clear()
            continue

        if event == 'start' and elem.tag == 'div':
            in_div = True
            continue
        if event == 'end' and elem.tag == 'div':
            #print('div data', elem.attrib, 'text', elem.text, 'iter', list(elem.itertext()))
            if elem.get('style', None) != 'visibility:hidden':
                data_strs.extend([ x.strip() for x in elem.itertext() ])
            in_div = False
            elem.clear()
            continue
        if not in_div:
            if event == 'end':
                elem.clear()
            continue

        if elem.tag == 'br':
            continue

        if event == 'end':
            elem.clear()
    return convert_to_dicts(records)


