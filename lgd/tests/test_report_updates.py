import csv
import tempfile
import unittest
from concurrent.futures import Future
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scrape.base import BaseDownloader, Context, Params
from scrape.directory import DirectoryDownloader, TraditionalLocalBodiesDownloader
from scrape.site_map import get_known_site_map
from scrape.transactions import (TransactionCaptchaError, TransactionRangeDownloader,
                                 TransactionsDownloader, missing_date_ranges,
                                 parse_transaction_report)
from scrape.__main__ import Joiner


REPORT = '''<script>var error = 'The CAPTCHA image code was entered incorrectly.';</script>
<table id="lgd_transaction_report"><thead><tr><th>S No</th><th>Transaction ID</th>
<th>Operation Code</th><th>Operation Name</th><th>Description</th><th>Transaction Date</th>
</tr></thead><tbody><tr><td>1</td><td>850795</td><td>45</td><td>Rename</td>
<td>The Village Panchayat 'Bamroli' is renamed as 'Bamroli (V)' (Code:166501).</td>
<td>18-Jan-2024</td></tr></tbody></table>'''


class TransactionParsingTests(unittest.TestCase):
    def test_success_ignores_captcha_error_in_javascript(self):
        records = parse_transaction_report(REPORT)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['Transaction ID'], '850795')
        self.assertIn('(Code:166501)', records[0]['Description'])
        self.assertNotIn('Entity Code', records[0])

    def test_explicit_empty_result(self):
        self.assertEqual(parse_transaction_report('<div>No Record Found</div>'), [])

    def test_unexpected_page_is_not_an_empty_success(self):
        with self.assertRaises(ValueError):
            parse_transaction_report('<html><body>LGD is unavailable</body></html>')

    def test_captcha_validation_error(self):
        for markup in (
            '<span id="errorcaptchaAnswers">The CAPTCHA image code was entered incorrectly.</span>',
            '<span id="errorcaptchaAnswers"></span><span class="mandatory"><strong>'
            'The CAPTCHA image code was entered incorrectly. Enter the text shown above.</strong></span>',
        ):
            with self.subTest(markup=markup), self.assertRaises(TransactionCaptchaError):
                parse_transaction_report(markup)

    def test_schema_drift_fails(self):
        with self.assertRaises(ValueError):
            parse_transaction_report(REPORT.replace('Transaction ID', 'New ID'))

    def test_incomplete_results_table_is_not_an_empty_success(self):
        with self.assertRaisesRegex(ValueError, 'results table is empty'):
            parse_transaction_report(REPORT.split('<tbody>', 1)[0] + '<tbody></tbody></table>')

    def test_missing_month_ranges_are_inclusive_and_skip_covered_dates(self):
        self.assertEqual(list(missing_date_ranges(date(2024, 1, 30), date(2024, 3, 1), {'2024-02-02'})), [
            (date(2024, 1, 30), date(2024, 1, 31)),
            (date(2024, 2, 1), date(2024, 2, 1)),
            (date(2024, 2, 3), date(2024, 2, 29)),
            (date(2024, 3, 1), date(2024, 3, 1)),
        ])


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(BaseDownloader.clear_cache)
        self.params = Params()
        self.params.base_raw_dir = self.temp.name
        self.params.transactions_start_date = '2024-01-30'
        self.ctx = Context(self.params)
        BaseDownloader.set_known_site_map(get_known_site_map())

    def test_all_three_tlb_levels_have_uniform_columns_and_distinct_codes(self):
        downloader = TraditionalLocalBodiesDownloader(name='TRADITIONAL_LOCAL_BODIES', ctx=self.ctx)
        children = downloader.get_child_downloaders()
        self.assertEqual(len(children), 3)
        rows = []
        for child in children:
            level, prefix = child.LEVELS[child.post_data['TlbLocalBodyType']]
            source = {'S.No.': '1', 'State Code': '18', 'State Name': 'Assam',
                      'District Level TLB Code': '100', 'District Level TLB Name': 'Council',
                      'Intermediate/Block Level TLB Code': '200', 'Intermediate/Block Level TLB Name': 'Block',
                      'Gram/Village Level TLB Code': '300', 'Gram/Village Level TLB Name': 'Village'}
            with patch.object(DirectoryDownloader, 'get_records', return_value=[source]):
                row = child.get_records()[0]
            self.assertEqual(row['Local Body Level'], level)
            self.assertEqual(row['Local Body Code'], source[prefix + ' Code'])
            for obsolete in ('Localbody Type Name', 'Localbody Type Code',
                             'Local Body Version', 'Local Body Name (In Local)'):
                self.assertNotIn(obsolete, row)
            rows.append(row)
        self.assertEqual([r['Local Body Code'] for r in rows], ['100', '200', '300'])
        self.assertEqual([list(r) for r in rows], [list(rows[0])] * 3)
        self.assertEqual([r['District Panchayat Code'] for r in rows], ['', '100', '100'])
        self.assertEqual([r['Intermediate/Block Panchayat Code'] for r in rows], ['', '', '200'])

    def test_backfill_includes_center_all_states_and_only_complete_days(self):
        downloader = TransactionsDownloader(name='TRANSACTIONS', ctx=self.ctx)
        with patch.object(BaseDownloader, 'records_from_downloader', return_value=[
            {'State Code': '24', 'State Name (In English)': 'Gujarat'}
        ]), patch('scrape.transactions.get_date_str', return_value='02Feb2024'):
            children = downloader.get_child_downloaders()
        self.assertEqual(len(children), 4)
        self.assertEqual({c.state_code for c in children}, {'0', '24'})
        self.assertEqual(downloader.requested_dates, {'2024-01-30', '2024-01-31', '2024-02-01'})
        self.assertIn('/transactions/parts/', children[0].get_filename())
        self.assertFalse(downloader.coverage_file.exists())

    def test_history_merge_is_idempotent_but_keeps_distinct_descriptions(self):
        downloader = TransactionsDownloader(name='TRANSACTIONS', ctx=self.ctx)
        record = dict(parse_transaction_report(REPORT)[0], **{'State Code': '24', 'State Name': 'Gujarat'})
        downloader.history_dir.mkdir()
        with downloader.previous_file.open('w') as output:
            writer = csv.DictWriter(output, fieldnames=record)
            writer.writeheader()
            writer.writerow(record)
        with patch('scrape.base.MultiDownloader.combine_records', return_value=[record, dict(record, Description='Another operation detail')]):
            records = downloader.combine_records()
        self.assertEqual(len(records), 2)

    def test_missing_history_never_advances_coverage(self):
        downloader = TransactionsDownloader(name='TRANSACTIONS', ctx=self.ctx)
        downloader.history_dir.mkdir()
        downloader.coverage_file.write_text('2024-01-30\n')
        with self.assertRaises(ValueError):
            downloader.get_child_downloaders()

    def test_same_day_backfill_can_be_widened_and_preserves_empty_coverage(self):
        with patch.object(BaseDownloader, 'records_from_downloader', return_value=[
            {'State Code': '24', 'State Name (In English)': 'Gujarat'}
        ]), patch('scrape.transactions.get_date_str', return_value='02Feb2024'), \
                patch.object(TransactionRangeDownloader, 'get_records', return_value=[]) as fetch:
            self.params.transactions_start_date = '2024-02-01'
            first = TransactionsDownloader(name='TRANSACTIONS', ctx=self.ctx)
            first.download()
            self.assertTrue(first.is_done())
            self.assertEqual(first.coverage_file.read_text().splitlines(), ['2024-02-01'])
            self.assertTrue(first.previous_file.read_text().startswith('Transaction ID,'))
            fetch.reset_mock()

            self.params.transactions_start_date = '2024-01-30'
            wider = TransactionsDownloader(name='TRANSACTIONS', ctx=self.ctx)
            self.assertFalse(wider.is_done())
            wider.download()
            self.assertEqual(fetch.call_count, 2)
            self.assertTrue(wider.is_done())
            self.assertEqual(wider.coverage_file.read_text().splitlines(),
                             ['2024-01-30', '2024-01-31', '2024-02-01'])

    def test_failed_state_does_not_advance_coverage_and_completed_parts_are_reused(self):
        with patch.object(BaseDownloader, 'records_from_downloader', return_value=[
            {'State Code': '24', 'State Name (In English)': 'Gujarat'}
        ]), patch('scrape.transactions.get_date_str', return_value='31Jan2024'):
            downloader = TransactionsDownloader(name='TRANSACTIONS', ctx=self.ctx)
            with patch.object(TransactionRangeDownloader, 'get_records', side_effect=[[], ValueError('unavailable')]):
                with self.assertRaisesRegex(ValueError, 'unavailable'):
                    downloader.download()
            self.assertFalse(downloader.coverage_file.exists())
            self.assertFalse(downloader.is_done())
            with patch.object(TransactionRangeDownloader, 'get_records', return_value=[]) as fetch:
                downloader.download()
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(downloader.coverage_file.read_text().splitlines(), ['2024-01-30'])

    def test_interrupted_range_write_is_not_accepted_as_a_complete_checkpoint(self):
        for error_type in (OSError, KeyboardInterrupt):
            with self.subTest(error=error_type.__name__):
                downloader = TransactionRangeDownloader(
                    name=f'TEST_{error_type.__name__}', base_name='TRANSACTIONS', ctx=self.ctx,
                    state_code='24', state_name='Gujarat', start_date='2024-01-01', end_date='2024-01-31',
                    csv_filename=f'{error_type.__name__}.csv')
                filename = Path(downloader.get_filename())
                records = [{'Transaction ID': '1'}, {'Transaction ID': '2'}]
                original = csv.DictWriter.writerow

                def fail_on_second_row(writer, row):
                    self.assertFalse(filename.exists())
                    if row['Transaction ID'] == '2':
                        raise error_type('interrupted write')
                    return original(writer, row)

                with patch.object(downloader, 'get_records', return_value=records), \
                        patch.object(csv.DictWriter, 'writerow', new=fail_on_second_row):
                    with self.assertRaises(error_type):
                        downloader.download()
                self.assertFalse(downloader.is_done())
                # A hard process kill can leave a temporary file. It must not
                # be mistaken for a finished download on the next attempt.
                Path(str(filename) + '.tmp').write_text('partial stale data')
                with patch.object(downloader, 'get_records', return_value=records) as fetch:
                    downloader.download()
                self.assertEqual(fetch.call_count, 1)
                with filename.open() as source:
                    self.assertEqual(list(csv.DictReader(source)), records)

    def test_aggregate_failure_propagates_to_the_workflow(self):
        parent = Future()
        child = Future()
        child.set_result(None)
        joiner = Joiner(parent, {'child'}, object())
        with patch('scrape.__main__.download_task', side_effect=ValueError('bad aggregate')):
            joiner.get_checker('child')(child)
        with self.assertRaisesRegex(ValueError, 'bad aggregate'):
            parent.result()


if __name__ == '__main__':
    unittest.main()
