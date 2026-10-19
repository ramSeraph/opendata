import contextlib
import io
import unittest
from unittest.mock import patch

import requests

import check_districts
import check_states
import check_subdistricts
import common


URL = 'https://lgdirectory.gov.in/globalviewSubDistrictDetail.do'
PARAMS = {'globalsubdistrictId': '7551'}
VALID_HTML = '<table><tr><td>Effective Date</td><td> 24/09/2025 </td></tr></table>'


def response(status=200, html=VALID_HTML):
    result = requests.Response()
    result.status_code = status
    result.url = URL + '?globalsubdistrictId=7551'
    result._content = html.encode()
    return result


class EffectiveDateTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.fetch = self.enterContext(patch.object(common.requests, 'get'))
        self.sleep = self.enterContext(patch.object(common.time, 'sleep'))

    def test_success_handles_whitespace_and_nested_tables(self):
        self.fetch.return_value = response(html=f'<table><tr><td>{VALID_HTML}</td></tr></table>')
        self.assertEqual(common.get_effective_date(URL, PARAMS), '24Sep2025')
        self.fetch.assert_called_once_with(URL, params=PARAMS, timeout=(10, 60))
        self.sleep.assert_not_called()

    def test_transient_http_and_transport_errors_are_retried(self):
        for error in [response(503), response(504), requests.Timeout('timeout'), requests.ConnectionError('reset')]:
            with self.subTest(error=error):
                self.fetch.reset_mock()
                self.sleep.reset_mock()
                self.fetch.side_effect = [error, response()]
                self.assertEqual(common.get_effective_date(URL, PARAMS), '24Sep2025')
                self.assertEqual(self.fetch.call_count, 2)
                self.sleep.assert_called_once_with(2)

    def test_retries_are_bounded_and_http_error_identifies_url_and_status(self):
        self.fetch.side_effect = [response(503) for _ in range(3)]
        with self.assertRaisesRegex(requests.HTTPError, '503.*globalsubdistrictId=7551'):
            common.get_effective_date(URL, PARAMS)
        self.assertEqual(self.fetch.call_count, 3)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [2, 4])

    def test_permanent_http_failure_is_not_retried(self):
        self.fetch.return_value = response(404)
        with self.assertRaises(requests.HTTPError):
            common.get_effective_date(URL, PARAMS)
        self.assertEqual(self.fetch.call_count, 1)
        self.sleep.assert_not_called()

    def test_missing_empty_or_invalid_date_is_reported_as_unavailable(self):
        for html in [
            '<html>Service unavailable</html>',
            '<table><tr><td>Effective Date</td></tr></table>',
            '<table><tr><td>Effective Date</td><td></td></tr></table>',
            '<table><tr><td>Effective Date</td><td>31/02/2025</td></tr></table>',
        ]:
            with self.subTest(html=html):
                self.fetch.return_value = response(html=html)
                with self.assertRaisesRegex(ValueError, 'Effective Date'):
                    common.get_effective_date(URL, PARAMS)
        self.sleep.assert_not_called()


class MissingEntityDateTests(unittest.TestCase):
    def test_all_date_consumers_keep_missing_entities_without_an_inception(self):
        cases = [
            (check_states, {'State or UT': 'S'}),
            (check_districts, {'State Code': '6', 'State Name (In English)': 'Haryana'}),
            (check_subdistricts, {
                'State Code': '6', 'State Name': 'Haryana',
                'District Code': '100', 'District Name': 'Example district',
            }),
        ]
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(patch.object(check_districts, 'g_wd_state_map_rev', {'6': 'Q1174'}))
            stack.enter_context(patch.object(check_subdistricts, 'g_wd_dist_map_rev', {'100': 'Q2001'}))
            stack.enter_context(patch.object(common, 'get_wd_data', return_value={}))
            for checker, fields in cases:
                for failure in [requests.HTTPError('503 Server Error'), requests.Timeout('timed out'),
                                ValueError('LGD page has no Effective Date')]:
                    with self.subTest(checker=checker.__name__, failure=failure):
                        data = {'1': {'Code': '1', 'Name': 'Example', **fields}}
                        with patch.object(common, 'get_lgd_data', return_value=data), \
                             patch.object(common, 'get_effective_date', side_effect=failure):
                            report = common.base_entity_checks(
                                lgd_id_key='Code', lgd_name_key='Name',
                                lgd_url_fn=lambda code: {'base': URL, 'params': PARAMS},
                                lgd_correction_fn=checker.get_correction_info,
                            )
                        self.assertEqual(len(report['missing']), 1)
                        missing = report['missing'][0]
                        self.assertEqual(missing['lgd_entry']['lgd_code'], '1')
                        self.assertNotIn('Effective Date', missing['lgd_entry'])
                        self.assertEqual(missing['lgd_entry']['Effective Date Error'], str(failure))
                        self.assertIsNone(missing['correction_info']['inception'])
                correction = checker.get_correction_info({
                    'lgd_code': '1', 'lgd_name': 'Example', 'Effective Date': '24Sep2025', **fields,
                })
                self.assertEqual(correction['inception'], '+2025-09-24T00:00:00Z/11')


if __name__ == '__main__':
    unittest.main()
