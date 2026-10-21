import csv
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape
from zipfile import ZipFile

import requests

from scrape.base import BaseDownloader, Context, Params
from scrape.directory import get_all_directory_downloaders
from scrape.site_map import get_known_site_map


HEADER = ['S.No.', 'Admin Unit Entity Code', 'Admin Unit Entity Name',
          'Admin Unit Entity Name (Local)']


def workbook(rows):
    """Small OOXML workbook matching LGD's title/header/data layout."""
    out = io.BytesIO()
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    xml_rows = []
    for number, row in enumerate(rows, 1):
        cells = ''.join(f'<c r="{chr(65+i)}{number}" t="inlineStr"><is><t>'
                        f'{escape(value)}</t></is></c>' for i, value in enumerate(row))
        xml_rows.append(f'<row r="{number}">{cells}</row>')
    with ZipFile(out, 'w') as z:
        z.writestr('[Content_Types].xml',
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/_rels/workbook.xml.rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                   '</Types>')
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="{rel}">'
                   '<sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels',
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'<Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/>'
                   '</Relationships>')
        z.writestr('xl/worksheets/sheet1.xml',
                   f'<worksheet xmlns="{ns}"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>')
    response = requests.Response()
    response.status_code = 200
    response._content = out.getvalue()
    response.headers.update({'Content-Disposition': 'attachment; filename=report.xlsx',
                             'Content-Type': 'application/vnd.openxmlformats-officedocument.'
                                             'spreadsheetml.sheet;charset=UTF-8'})
    return response


class AdministrativeUnitDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(BaseDownloader.clear_cache)
        BaseDownloader.set_known_site_map(get_known_site_map())
        self.temp = self.enterContext(TemporaryDirectory())
        params = Params()
        params.base_raw_dir = self.temp + '/raw'
        params.temp_dir = self.temp + '/temp'
        self.ctx = Context(params)
        self.ctx._csrf_token = 'test-token'
        self.downloaders = {d.name: d for d in get_all_directory_downloaders(self.ctx)}

    def child(self, scope='CENTRAL'):
        parent = self.downloaders[f'{scope}_ADMIN_DEPT_UNITS']
        level = {'adminUnitCode': '1150', 'adminLevelNameEng': 'Postal Circle'}
        if scope == 'STATE':
            level.update({'State Code': '20', 'State Name': 'Jharkhand'})
        with patch.object(BaseDownloader, 'records_from_downloader', return_value=[level]):
            child, = parent.get_child_downloaders()
        self.assertEqual(parent.deps, [f'{scope}_ADMIN_DEPTS'])
        return parent, child

    def response(self, child, rows):
        self.enterContext(patch.object(child.captcha_helper, 'get_code', return_value='123456'))
        return self.enterContext(patch.object(child, 'post_with_progress', return_value=workbook(rows)))

    def test_real_xlsx_parsing_and_combination_preserve_rows_and_level(self):
        for scope in ('CENTRAL', 'STATE'):
            with self.subTest(scope=scope):
                parent, child = self.child(scope)
                post = self.response(child, [
                    ['Administrative Unit Level Wise Administrative Unit Entity'], HEADER,
                    ['1', '51466', 'Andhra Pradesh', ''], ['2', '51469', 'Assam', 'অসম'],
                ])
                parent.download()
                with Path(parent.get_filename()).open() as f:
                    rows = list(csv.DictReader(f))
                self.assertEqual([r['Admin Unit Entity Code'] for r in rows], ['51466', '51469'])
                self.assertEqual(rows[1]['Admin Unit Entity Name (Local)'], 'অসম')
                self.assertEqual(rows[0]['Admin Department Code'], '1150')
                self.assertEqual(rows[0]['Admin Department Name'], 'Postal Circle')
                if scope == 'STATE':
                    self.assertEqual(rows[0]['State Code'], '20')
                self.assertEqual(post.call_args.kwargs['data']['downloadType'], 'xls')
                self.assertEqual(post.call_args.kwargs['data']['lbl'], 'FOOBAR')

    def test_title_as_header_cannot_be_accepted_as_empty_data(self):
        _, child = self.child()
        child.xlsx_conv_args = {}  # Reproduce the retired child's lost parser settings.
        self.response(child, [['Report title', ' ', ' ', ' '], HEADER,
                              ['1', '51466', 'Andhra Pradesh', '']])
        with self.assertRaisesRegex(ValueError, 'header'):
            child.download()
        self.assertFalse(Path(child.get_filename()).exists())

    def test_missing_prefix_or_code_does_not_create_completed_csv(self):
        for row in (['81', '51466', 'Andhra Pradesh', ''], ['1', '', 'Andhra Pradesh', '']):
            with self.subTest(row=row):
                _, child = self.child()
                self.response(child, [['Report title'], HEADER, row])
                with self.assertRaisesRegex(ValueError, 'row'):
                    child.download()
                self.assertFalse(Path(child.get_filename()).exists())

    def test_empty_selection_is_allowed_but_empty_whole_dataset_fails(self):
        parent, child = self.child()
        self.response(child, [['Report title'], HEADER])
        self.assertEqual(child.get_records(), [])
        with self.assertRaisesRegex(ValueError, 'No populated'):
            parent.download()
        self.assertFalse(Path(parent.get_filename()).exists())

    def test_parser_settings_survive_child_and_worker_reconstruction(self):
        parent = self.downloaders['CENTRAL_ADMIN_DEPT_UNITS']
        parent.excel_conv_args = {'header_row_span': 2}
        _, child = self.child()
        restored = BaseDownloader.from_dict(type(child).__name__, child.get_kwargs(),
                                            self.ctx.params.__dict__)
        self.assertEqual(restored.download_types, ['xls'])
        self.assertEqual(restored.xlsx_conv_args, {'header_row_span': 1})
        self.assertEqual(restored.excel_conv_args, {'header_row_span': 2})


if __name__ == '__main__':
    unittest.main()
