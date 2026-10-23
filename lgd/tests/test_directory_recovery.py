import unittest
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import requests

from scrape.base import BaseDownloader, Context, Params, INCORRECT_CAPTCHA_MESSAGE
from scrape.directory import get_all_directory_downloaders, UnexpectedDirectoryPage
from scrape.site_map import get_known_site_map
from tests.test_admin_unit_directory import workbook


HOME = ('<section id="hero"><a href="downloadDirectory.do?OWASP_CSRFTOKEN=new-download">'
        'Download Directory</a></section><div id="reports-model">'
        '<a href="report.do?OWASP_CSRFTOKEN=new-report">Report</a></div>')


def page(text, status=200):
    response = requests.Response()
    response.status_code = status
    response.headers['Content-Type'] = 'text/html;charset=UTF-8'
    response._content = text.encode()
    return response


class DirectoryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(BaseDownloader.clear_cache)
        BaseDownloader.set_known_site_map(get_known_site_map())
        temporary = self.enterContext(TemporaryDirectory())
        params = Params()
        params.base_raw_dir = temporary + '/raw'
        params.temp_dir = temporary + '/temp'
        params.captcha_retries = 1
        self.ctx = Context(params)
        self.ctx._csrf_token = 'old-download'
        self.old = self.ctx._session = Mock()
        self.fresh = Mock()
        self.fresh.get.return_value = page(HOME)
        self.enterContext(patch('scrape.base.requests.session', return_value=self.fresh))
        self.reset = self.enterContext(patch.object(self.ctx, 'reset_session', wraps=self.ctx.reset_session))
        self.sleep = self.enterContext(patch('scrape.directory.time.sleep'))
        parent = next(d for d in get_all_directory_downloaders(self.ctx) if d.name == 'STATE_ORG_UNITS')
        organization = {'Organization Code': '679', 'Organization Name': 'Supplies & Disposals',
                        'State Code': '6', 'State Name': 'Haryana'}
        with patch.object(BaseDownloader, 'records_from_downloader', return_value=[organization]):
            self.child, = parent.get_child_downloaders()
        self.captcha = self.enterContext(patch.object(self.child.captcha_helper, 'get_code',
                                                     side_effect=['old-answer', 'new-answer', 'third-answer']))

    def valid_workbook(self):
        header = ['S.No.', 'Org Unit Code', 'Org Unit Name (In English)', 'Org Unit Name (In Local)',
                  'Entity Type', 'Entity Lc', 'Parent Org Unit Code', 'Parent Org Unit Name',
                  'Org Located Level Code']
        return workbook([['Organization Units'], header,
                         ['1', '18104', 'Supplies & Disposals', '', '1', '6', '0', '', '1139']])

    def test_unexpected_page_retries_with_new_session_token_and_captcha(self):
        self.old.post.return_value = page('<title>Unavailable</title>')
        self.fresh.post.return_value = self.valid_workbook()
        self.child.download()
        rows = list(self.child.retrieve_records())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Org Unit Code'], '18104')
        self.reset.assert_called_once_with()
        self.old.close.assert_called_once_with()
        self.sleep.assert_called_once_with(5)
        self.assertEqual((self.old.post.call_count, self.fresh.post.call_count), (1, 1))
        for session, token, answer in [(self.old, 'old-download', 'old-answer'),
                                       (self.fresh, 'new-download', 'new-answer')]:
            sent = session.post.call_args.kwargs['data']
            self.assertEqual(sent['OWASP_CSRFTOKEN'], token)
            self.assertEqual(sent['captchaAnswer'], answer)
            self.assertEqual(sent['entityCodes'], ['35', '6', '679'])
            self.assertEqual(sent['rptFileName'], 'orgUnitBasedOnOrgCode')
        self.assertIn('new-download', self.captcha.call_args_list[1].args[0])

    def test_persistent_unexpected_page_fails_without_checkpoint_or_hidden_tokens(self):
        error = page('<title>Unavailable</title><input type="hidden" value="private-token">')
        self.old.post.return_value = error
        self.fresh.post.return_value = error
        with self.assertRaises(UnexpectedDirectoryPage) as failure:
            self.child.download()
        self.assertIn('Unavailable', str(failure.exception))
        self.assertNotIn('private-token', str(failure.exception))
        self.assertEqual((self.old.post.call_count, self.fresh.post.call_count), (1, 1))
        self.reset.assert_called_once_with()
        self.assertFalse(self.child.is_done())
        self.sleep.assert_called_once_with(5)

    def test_http_error_is_not_an_empty_report_or_session_retry(self):
        self.old.post.return_value = page('Not found', 404)
        with self.assertRaisesRegex(Exception, 'bad web request.. 404'):
            self.child.download()
        self.old.post.assert_called_once()
        self.reset.assert_not_called()
        self.assertFalse(self.child.is_done())

    def test_invalid_workbook_is_not_retried_or_checkpointed(self):
        broken = self.valid_workbook()
        broken._content = b'not a workbook'
        self.old.post.return_value = broken
        with self.assertRaises(Exception):
            self.child.download()
        self.old.post.assert_called_once()
        self.reset.assert_not_called()
        self.assertFalse(self.child.is_done())

    def test_captcha_failures_remain_bounded_without_resetting_session(self):
        self.old.post.return_value = page(INCORRECT_CAPTCHA_MESSAGE)
        with patch('scrape.directory.time.sleep'), self.assertRaisesRegex(Exception, 'captcha failed'):
            self.child.download()
        self.assertEqual(self.old.post.call_count, 2)
        self.reset.assert_not_called()
        self.assertFalse(self.child.is_done())

    def test_unexpected_page_does_not_consume_the_captcha_retry_budget(self):
        self.old.post.return_value = page('<title>Unavailable</title>')
        self.fresh.post.side_effect = [page(INCORRECT_CAPTCHA_MESSAGE), self.valid_workbook()]
        with patch('scrape.directory.time.sleep'):
            self.child.download()
        self.assertTrue(self.child.is_done())
        self.assertEqual((self.old.post.call_count, self.fresh.post.call_count), (1, 2))
        self.reset.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
