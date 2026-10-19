import io
import unittest

from odf.opendocument import OpenDocumentText
from odf.table import Table, TableCell, TableRow
from odf.text import P

from scrape.base import BaseDownloader, Context, Params
from scrape.conversion_helper import records_from_odt
from scrape.directory import get_all_directory_downloaders
from scrape.site_map import get_known_site_map


HEADER = ['S.No.', 'State Code', 'State Name', 'Parliament Constituency Code',
          'Parliament Constituency Name', 'Assembly Constituency Code',
          'Assembly Constituency Name']


def odt(tables):
    document = OpenDocumentText()
    for index, rows in enumerate(tables):
        table = Table(name=f'Page{index}')
        for values in rows:
            row = TableRow()
            for value in values:
                cell = TableCell()
                if value:
                    cell.addElement(P(text=value))
                row.addElement(cell)
            table.addElement(row)
        document.text.addElement(table)
    output = io.BytesIO()
    document.save(output)
    output.seek(0)
    return output


def data_row(serial):
    return [str(serial), '28', 'Andhra Pradesh', str(serial), f'PC {serial}', '', '']


class ODTConversionTests(unittest.TestCase):
    def test_all_pages_survive_with_or_without_introductory_tables(self):
        # Each current LGD table contains 40 data rows. The old converter
        # discarded the first two tables, silently losing serials 1 through 80.
        pages = [[HEADER] + [data_row(i) for i in range(start, start + 40)]
                 for start in (1, 41, 81)]
        for introductions in ([], [[['LGD report']]],
                              [[['LGD report']], [['Constituencies of India']]]):
            with self.subTest(introductions=len(introductions)):
                rows = records_from_odt(odt(introductions + pages), HEADER)
                self.assertEqual([r['S.No.'] for r in rows],
                                 [str(i) for i in range(1, 121)])
                self.assertEqual(rows[0]['Assembly Constituency Code'], '')
                self.assertEqual(rows[0]['Assembly Constituency Name'], '')

    def test_only_known_footers_are_removed_and_placeholders_survive(self):
        rows = records_from_odt(odt([
            [HEADER, ['1', '35', 'Andaman And Nicobar Islands', '543',
                      'Andaman & Nicobar Islands']],
            [HEADER, ['2', '28', 'Andhra Pradesh', '411', 'Amalapuram',
                      '3166', 'Amalapuram'], ['Oct 19, 2026, 4:45 PM']],
            [['URL http://lgdirectory.gov.in Report Generated on '
              'Oct 19, 2026, 4:45 PMLocal Government Directory']],
        ]), HEADER)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['Assembly Constituency Code'], '')
        self.assertEqual(rows[1]['Assembly Constituency Code'], '3166')

    def test_continuation_without_repeated_header_keeps_first_row(self):
        rows = records_from_odt(odt([[HEADER, data_row(1)], [data_row(2)]]), HEADER)
        self.assertEqual([r['S.No.'] for r in rows], ['1', '2'])

    def test_missing_prefix_gaps_and_duplicate_serials_fail(self):
        for serials in ((81, 82), (1, 3), (1, 1)):
            with self.subTest(serials=serials), self.assertRaisesRegex(ValueError, 'serial'):
                records_from_odt(odt([[HEADER] + [data_row(i) for i in serials]]), HEADER)

    def test_unrecognized_rows_are_not_silently_discarded(self):
        for row in (['Unexpected report warning'], data_row(2) + ['new value'],
                    ['Oct 19, 2026, 4:45 PM', 'unexpected data']):
            with self.subTest(row=row), self.assertRaises(ValueError):
                records_from_odt(odt([[HEADER, data_row(1), row]]), HEADER)

    def test_missing_or_changed_headers_fail(self):
        for pages in (
            [[['LGD report']]], [[HEADER]], [[data_row(1)]],
            [[HEADER[:-1], data_row(1)]],
            [[HEADER, data_row(1)], [HEADER[:-1] + ['New name'], data_row(2)]],
        ):
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                records_from_odt(odt(pages), HEADER)

    def test_internal_empty_cells_remain_empty_strings(self):
        row = data_row(1)
        row[2] = ''
        rows = records_from_odt(odt([[HEADER, row]]), HEADER)
        self.assertEqual(rows[0]['State Name'], '')

    def test_both_active_odt_downloaders_have_the_verified_schema(self):
        self.addCleanup(BaseDownloader.clear_cache)
        BaseDownloader.set_known_site_map(get_known_site_map())
        downloaders = get_all_directory_downloaders(Context(Params()))
        selected = [d for d in downloaders if 'odt' in getattr(d, 'download_types', [])]
        self.assertEqual({d.name for d in selected},
                         {'CONSTITUENCIES_PARLIAMENT', 'CONSTITUENCIES_ASSEMBLY'})
        for downloader in selected:
            self.assertEqual(list(downloader.expected_fields), HEADER)
            self.assertEqual(downloader.odt_conv_args, {})


if __name__ == '__main__':
    unittest.main()
