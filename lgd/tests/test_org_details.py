import unittest
from html import escape
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import requests

from scrape import get_all_downloaders
from scrape.base import BaseDownloader, Context, Params
from scrape.org_details import FIELDS, OrganizationDetailsDownloader, parse_organization_details
from scrape.site_map import get_known_site_map


ROW = ['1', '0', '', '19089', 'DEPARTMENT OF REVENUE', '00123',
       'office@example.org', '01772622382', 'OFFICE, SHIMLA', '1', 'State', '2',
       'Himachal Pradesh']


def report(rows):
    return ('<table id="table"><tr>'
            + ''.join(f'<th>{escape(h)}</th>' for h in FIELDS) + '</tr>'
            + ''.join('<tr>' + ''.join(f'<td>{escape(v)}</td>' for v in r)
                      + '</tr>' for r in rows) + '</table>')


def response(text):
    result = requests.Response()
    result.status_code = 200
    result._content = text.encode()
    return result


class DetailsParsingTests(unittest.TestCase):
    def test_contacts_and_codes_remain_text(self):
        row, = parse_organization_details(report([ROW]))
        self.assertEqual(row['Org Specific Code'], '00123')
        self.assertEqual(row['Organization Contact Number'], '01772622382')
        self.assertEqual(row['Organization Email ID'], 'office@example.org')
        self.assertEqual(row['Entity Code'], '2')
        self.assertEqual(row['Parent Org Unit Code'], '0')

    def test_missing_and_placeholder_values_and_variants_remain_distinct(self):
        blank, zero = ROW.copy(), ROW.copy()
        blank[8] = ''
        zero[0], zero[8] = '2', '0'
        rows = parse_organization_details(report([blank, zero]))
        self.assertEqual([r['Organization Address'] for r in rows], ['', '0'])
        self.assertEqual([r['Org Unit Code'] for r in rows], ['19089', '19089'])

    def test_negative_entity_types_are_distinct_code_spaces(self):
        for code, name in [('-3', 'Village Panchayat'), ('-100', '')]:
            values = ROW.copy()
            values[9:11] = [code, name]
            row, = parse_organization_details(report([values]))
            self.assertEqual(row['Entity Type'], code)
            self.assertEqual(row['Entity Type Name'], name)

    def test_valid_empty_report_differs_from_error_page(self):
        self.assertEqual(parse_organization_details(report([])), [])
        with self.assertRaises(ValueError):
            parse_organization_details('<html>SQLGrammarException</html>')

    def test_malformed_rows_fail_instead_of_being_silently_truncated(self):
        for content in [report([ROW]).replace('S.No', 'Serial'), report([ROW[:-1]]),
                        report([ROW]).replace('<td>1</td>', '<td>81</td>', 1),
                        report([ROW]).replace('<td>19089</td>', '<td></td>')]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_organization_details(content)


class DetailsDownloaderTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(BaseDownloader.clear_cache)
        BaseDownloader.set_known_site_map(get_known_site_map())
        self.temp = self.enterContext(TemporaryDirectory())
        params = Params()
        params.base_raw_dir = self.temp
        self.ctx = Context(params)
        self.ctx._csrf_token_reports = 'report-token'
        self.ctx._session = Mock()
        self.ctx.session.get.return_value = response('<form/>')

    def test_partition_registration_and_worker_serialization(self):
        parent = next(d for d in get_all_downloaders(self.ctx)
                      if d.name == 'ORG_UNIT_DETAILS')
        org = {'Organization Code': '697', 'Organization Name': 'Revenue',
               'State Code': '2', 'State Name': 'Himachal Pradesh'}
        with patch.object(BaseDownloader, 'records_from_downloader',
                          side_effect=[[], [org]]):
            child, = parent.get_child_downloaders()
        self.assertIsInstance(child, OrganizationDetailsDownloader)
        restored = BaseDownloader.from_dict(type(child).__name__, child.get_kwargs().copy(),
                                            self.ctx.params.__dict__.copy())
        self.assertEqual(restored.organization, org)

    def test_state_and_central_fields_captcha_retry_and_saved_schema(self):
        for state in (False, True):
            with self.subTest(state=state):
                org = {'Organization Code': '697', 'Organization Name': 'Revenue'}
                if state:
                    org.update({'State Code': '2', 'State Name': 'Himachal Pradesh'})
                child = OrganizationDetailsDownloader(
                    name=f'probe-{state}', base_name='ORG_UNIT_DETAILS', ctx=self.ctx,
                    csv_filename=f'probe-{state}.csv', organization=org)
                self.ctx.session.post.side_effect = [
                    response('The CAPTCHA image code was entered incorrectly.'),
                    response(report([ROW]))]
                with patch.object(child.captcha_helper, 'get_code', side_effect=['bad', 'good']):
                    child.download()
                row, = list(child.retrieve_records())
                self.assertEqual(set(row), set(child.expected_fields))
                self.assertEqual(row['State Code'], '2' if state else '0')
                sent = self.ctx.session.post.call_args.kwargs['data']
                self.assertEqual(sent['code'], '2' if state else '0')
                self.assertNotIn('statelabel', sent)
                self.assertEqual(sent['orgCode'], '697' if state else '')
                self.assertEqual(sent['orgUnitCode'], '0' if state else '697')
                self.assertNotIn('orgztn', sent)
                self.assertEqual(row['Base Organization Name'], 'Revenue')

    def test_problematic_heading_is_omitted_but_original_identity_is_saved(self):
        cases = [
            ('32', 'Kerala', '1533', 'PCCF & CWW - To be deleted', '1349622'),
            ('4', 'Chandigarh', '849', 'Food & Supplies & Consumer Affairs', '1236984'),
        ]
        for state, state_name, code, name, unit in cases:
            with self.subTest(organization=code):
                org = {'Organization Code': code, 'Organization Name': name,
                       'State Code': state, 'State Name': state_name}
                child = OrganizationDetailsDownloader(
                    name=f'heading-{code}', base_name='ORG_UNIT_DETAILS', ctx=self.ctx,
                    csv_filename=f'heading-{code}.csv', organization=org)
                values = ROW.copy()
                values[3:5] = [unit, name.upper()]
                values[11:13] = [state, state_name]

                def post(url, *, data, **kwargs):
                    self.assertEqual((data['code'], data['orgCode']), (state, code))
                    result = response(report([values]))
                    if data.get('orgztn'):
                        result = response('The Specified URL can not be found.')
                        result.status_code = 404
                    return result

                self.ctx.session.post.side_effect = post
                with patch.object(child.captcha_helper, 'get_code', return_value='123456'):
                    child.download()
                row, = child.retrieve_records()
                self.assertEqual(row['Org Unit Code'], unit)
                self.assertEqual(row['Org Unit Name (In English)'], name.upper())
                self.assertEqual(row['Base Organization Code'], code)
                self.assertEqual(row['Base Organization Name'], name)

    def test_unresolved_http_404_still_does_not_produce_an_empty_checkpoint(self):
        child = OrganizationDetailsDownloader(
            name='missing', base_name='ORG_UNIT_DETAILS', ctx=self.ctx,
            organization={'Organization Code': '1', 'Organization Name': 'Example'})
        result = response('The Specified URL can not be found.')
        result.status_code = 404
        self.ctx.session.post.return_value = result
        with patch.object(child.captcha_helper, 'get_code', return_value='123456'):
            with self.assertRaises(requests.HTTPError):
                child.download()
        self.assertFalse(child.is_done())

    def test_successful_http_error_page_is_not_checkpointed_as_empty_data(self):
        child = OrganizationDetailsDownloader(
            name='bad', base_name='ORG_UNIT_DETAILS', ctx=self.ctx,
            organization={'Organization Code': '1', 'Organization Name': 'Example'})
        self.ctx.session.post.return_value = response('<html>Something went wrong</html>')
        with patch.object(child.captcha_helper, 'get_code', return_value='123456'):
            with self.assertRaises(ValueError):
                child.download()
        self.assertFalse(child.is_done())


if __name__ == '__main__':
    unittest.main()
