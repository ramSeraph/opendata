import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scrape.base import BaseDownloader, Context, Params
from scrape.directory import get_all_directory_downloaders
from scrape.site_map import get_known_site_map
from tests.test_admin_unit_directory import workbook
from utils import daily_workflow, generate_daily_workflow


PRI = 'CONSTITUENCIES_MAPPINGS_PRI'
PARLIAMENT = 'PARLIAMENT_CONSTITUENCIES_LOCAL_BODY_MAPPINGS'
PRI_HEADER = [
    'S.No.', 'Parliament Constituency code', 'Parliament Constituency ECI Code',
    'Parliament Constituency Name', 'Assembly Constituency Code',
    'Assembly Constituency ECI Code', 'Assembly Constituency Name',
    'District Code', 'District Name', 'District Census 2011 Code',
    'Subdistrict Code', 'Subdistrict Name', 'Subdistrict Census 2011 Code',
    'Village Code', 'Village Name', 'Village Census 2011 Code',
    'Rural Localbody Code', 'Rural LocalbodyName', 'Block Code', 'Block Name',
]
PARLIAMENT_HEADER = ['S.No.', 'Parliament', 'Assembly', 'Classification',
                     'Local Gov. Name', 'Coverage']
STATE = {'State Code': '30', 'State Name (In English)': 'GOA'}
CONSTITUENCY = {'State Code': '30', 'State Name': 'GOA',
                'Parliament Constituency Code': '480',
                'Parliament Constituency Name': 'North Goa'}


class ConstituencyDirectoryTests(unittest.TestCase):
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

    def child(self, name):
        parent = self.downloaders[name]
        selection = STATE if name == PRI else CONSTITUENCY
        with patch.object(BaseDownloader, 'records_from_downloader', return_value=[selection]):
            child, = parent.get_child_downloaders()
        return parent, child

    def response(self, child, rows):
        self.enterContext(patch.object(child.captcha_helper, 'get_code', return_value='123456'))
        return self.enterContext(patch.object(child, 'post_with_progress', return_value=workbook(rows)))

    def read(self, parent):
        with Path(parent.get_filename()).open() as f:
            return list(csv.DictReader(f))

    def test_pri_xlsx_preserves_first_row_eci_codes_and_distinct_block_links(self):
        parent, child = self.child(PRI)
        first = ['1', '480', '01', 'North Goa', '3677', '10', 'Aldona',
                 '551', 'North Goa', '585', '5612', 'Bardez', '05607',
                 '626704', 'Aldona', '626704', '254349', 'Aldona', '5929', 'Bardez']
        second = first.copy()
        second[0], second[-2], second[-1] = '2', '6000', 'Another reported block'
        post = self.response(child, [['PRI constituency mapping'], PRI_HEADER, first, second])
        parent.download()
        rows = self.read(parent)
        self.assertEqual(len(rows), 2)
        self.assertEqual([r['S.No.'] for r in rows], ['1', '2'])
        self.assertEqual([r['Block Code'] for r in rows], ['5929', '6000'])
        self.assertEqual(rows[0]['Parliament Constituency ECI Code'], '01')
        self.assertEqual(rows[0]['State Code'], '30')
        self.assertEqual(set(rows[0]), set(PRI_HEADER) | {'State Code'})
        data = post.call_args.kwargs['data']
        self.assertEqual(data['rptFileName'], 'parlimentConstituencyAndAssemblyConstituencyPRI')
        self.assertEqual(data['entityCodes'], '30')
        self.assertEqual(data['stateName'], 'GOA')

    def test_parliament_xlsx_keeps_blank_and_conflicting_coverage_and_selection_codes(self):
        parent, child = self.child(PARLIAMENT)
        post = self.response(child, [['Parliament Wise Local Body Mapping'], PARLIAMENT_HEADER,
            ['1', 'North Goa', 'Bicholim', 'District Panchayat', 'North Goa', ''],
            ['2', 'North Goa', 'Bicholim', 'Village Panchayat', 'Naroa', 'F'],
            ['3', 'North Goa', 'Bicholim', 'Village Panchayat', 'Naroa', 'P'],
        ])
        parent.download()
        rows = self.read(parent)
        self.assertEqual([r['Coverage'] for r in rows], ['', 'F', 'P'])
        self.assertEqual([r['S.No.'] for r in rows], ['1', '2', '3'])
        self.assertTrue(all(r['State Code'] == '30' and
                            r['Parliament Constituency Code'] == '480' for r in rows))
        self.assertEqual(set(rows[0]), set(PARLIAMENT_HEADER) |
                         {'State Code', 'Parliament Constituency Code'})
        data = post.call_args.kwargs['data']
        self.assertEqual(data['rptFileName'], 'parliamentConstituency@state#parliament')
        self.assertEqual(data['entityCodes'], ['30', '480'])

    def test_empty_workbook_selection_does_not_create_a_fake_data_row(self):
        for name, header in ((PRI, PRI_HEADER), (PARLIAMENT, PARLIAMENT_HEADER)):
            with self.subTest(component=name):
                parent, child = self.child(name)
                self.response(child, [['Report title'], header])
                parent.download()
                self.assertEqual(self.read(parent), [])

    def test_parser_options_survive_child_and_worker_reconstruction(self):
        for name in (PRI, PARLIAMENT):
            with self.subTest(component=name):
                parent = self.downloaders[name]
                parent.excel_conv_args = {'header_row_span': 2}
                parent.odt_conv_args = {'record_tag': 'unused-test-option'}
                parent.download_types = ['xls', 'odt']
                parent.transform = ['ignore_if_empty_field', 'S.No.']
                _, child = self.child(name)
                restored = BaseDownloader.from_dict(type(child).__name__, child.get_kwargs(),
                                                    self.ctx.params.__dict__)
                self.assertEqual(restored.xlsx_conv_args, {'header_row_span': 1})
                self.assertEqual(restored.excel_conv_args, parent.excel_conv_args)
                self.assertEqual(restored.odt_conv_args, parent.odt_conv_args)
                self.assertEqual(restored.download_types, parent.download_types)
                self.assertEqual(restored.transform, parent.transform)

    def test_restored_sources_have_unique_metadata_and_real_workflow_dependencies(self):
        known = get_known_site_map()
        items = daily_workflow.downloaders()
        workflow = generate_daily_workflow.generate(items)
        for name, filename, dependency, label in (
            (PRI, 'constituencies_mapping_pri.csv', 'STATES',
             'State Wise Parliament Constituency and Assembly Constituency along with coverage details PRI'),
            (PARLIAMENT, 'parliament_constituencies_lb_mapping.csv', 'CONSTITUENCIES_PARLIAMENT',
             'Parliament Wise Local Body Mapping'),
        ):
            with self.subTest(component=name):
                entries = [e for e in known if e.get('file') == filename]
                self.assertEqual(len(entries), 1)
                entry, = entries
                self.assertEqual(entry['comp'], name)
                self.assertTrue(entry.get('listed', True))
                self.assertEqual(entry['dropdown'][-1], label)
                self.assertEqual(sum(e['dropdown'] == entry['dropdown'] for e in known), 1)
                self.assertNotIn('ignore_reason', entry)
                self.assertEqual(items[name].deps, [dependency])
                self.assertEqual(items[name].csv_filename, filename)
                self.assertIn(f'  {name}:\n    needs: [Prepare, {dependency}]\n', workflow)
        self.assertNotIn('NOFN_PANCHAYATS', items)


if __name__ == '__main__':
    unittest.main()
