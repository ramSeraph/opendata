import logging
import pickle
import unittest
from tempfile import TemporaryDirectory
from threading import local
from unittest.mock import Mock, patch

import requests

from scrape import base
from scrape.base import Context, Params, IntermittentFailureException
from scrape.dwr import DwrCaller, DwrDownloader
from scrape.org_coverage import OrganizationCoverageDownloader
from scrape.site_map import get_known_site_map


def response(content, content_type='text/html'):
    result = requests.Response()
    result.status_code = 200
    result.headers['Content-Type'] = content_type
    result._content = content.encode()
    return result


HOME = ('<section id="hero"><a href="downloadDirectory.do?OWASP_CSRFTOKEN=new-download">'
        'Download Directory</a></section><div id="reports-model">'
        '<a href="report.do?OWASP_CSRFTOKEN=new-report">Report</a></div>')


class SessionRecoveryTests(unittest.TestCase):
    def test_token_pair_is_not_partially_published_on_parse_failure(self):
        ctx = Context(Params())
        ctx._session = Mock()
        ctx.session.get.return_value = response(HOME.split('<div', 1)[0])
        with self.assertRaises(IntermittentFailureException):
            ctx.set_csrf_tokens()
        self.assertIsNone(ctx._csrf_token)
        self.assertIsNone(ctx._csrf_token_reports)

    def test_recovery_discards_all_state_from_the_replaced_http_session(self):
        ctx = Context(Params())
        old = ctx._session = Mock()
        old.get.return_value = response('<html>temporarily missing home page</html>')
        ctx._csrf_token = 'old-download'
        ctx._csrf_token_reports = None
        ctx.script_session_id = 'old-dwr/old-page'
        ctx.script_batch_id = 17
        ctx.dwr_session_id = 'old-dwr'
        ctx.dwr_page_id = 'old-page'
        ctx.dwr_instance_id = 3
        fresh = Mock()
        fresh.get.return_value = response(HOME)
        with patch('scrape.base.requests.session', return_value=fresh), \
                patch('scrape.base.time.sleep'):
            self.assertEqual(ctx.csrf_token_reports, 'new-report')
        old.close.assert_called_once_with()
        self.assertIs(ctx.session, fresh)
        self.assertEqual(ctx.csrf_token, 'new-download')
        self.assertEqual(ctx.script_session_id, '')
        self.assertEqual(ctx.script_batch_id, 0)
        self.assertIsNone(getattr(ctx, 'dwr_session_id', None))
        self.assertIsNone(getattr(ctx, 'dwr_page_id', None))
        self.assertIsNone(getattr(ctx, 'dwr_instance_id', None))

    def test_dwr_initializes_after_any_csrf_session_recovery(self):
        ctx = Context(Params())
        old = ctx._session = Mock()
        old.get.return_value = response('<html>temporarily missing home page</html>')
        ctx.script_session_id = 'old-dwr/old-page'
        ctx.script_batch_id = 17
        ctx.dwr_session_id = 'old-dwr'
        ctx.dwr_page_id = 'old-page'
        fresh = Mock()
        fresh.cookies = requests.cookies.RequestsCookieJar()
        fresh.get.return_value = response(HOME)
        def post(url, *, data, **kwargs):
            if url.endswith('/__System.generateId.dwr'):
                return response("dwr.engine.remote.handleCallback('0','0','fresh-dwr');", 'text/javascript')
            if 'scriptSessionId=fresh-dwr/' in data:
                return response("dwr.engine.remote.handleCallback('1','0',[]);", 'text/javascript')
            stale = response('Request used a stale DWR session')
            stale.status_code = 404
            return stale
        fresh.post.side_effect = post
        caller = DwrCaller(ctx=ctx, base_url='https://example.test', script_name='Department',
                           method_name='levels', call_args={'c0-param0': 'number:2078'})
        with patch('scrape.base.requests.session', return_value=fresh), \
                patch('scrape.base.time.sleep'):
            self.assertEqual(caller.call(), [])
        self.assertEqual(fresh.post.call_count, 2)
        generate, lookup = fresh.post.call_args_list
        self.assertTrue(generate.args[0].endswith('/__System.generateId.dwr'))
        self.assertIn('batchId=0\n', generate.kwargs['data'])
        self.assertIn('scriptSessionId=fresh-dwr/', lookup.kwargs['data'])
        self.assertIn('c0-param0=number:2078', lookup.kwargs['data'])
        self.assertNotIn('old-', lookup.kwargs['data'])
        self.assertEqual(ctx.script_batch_id, 2)

    def test_persistently_incomplete_home_page_still_fails_after_bounded_recovery(self):
        ctx = Context(Params())
        session = Mock()
        session.get.return_value = response(HOME.split('<div', 1)[0])
        with patch('scrape.base.requests.session', return_value=session), \
                patch('scrape.base.time.sleep') as sleep, \
                patch('scrape.base.logger'):
            with self.assertRaises(IntermittentFailureException):
                _ = ctx.csrf_token
        self.assertEqual(session.get.call_count, 4)
        self.assertEqual(sleep.call_count, 3)
        self.assertIsNone(ctx._csrf_token)
        self.assertIsNone(ctx._csrf_token_reports)

    def test_worker_rebinds_transported_downloader_and_all_session_consumers(self):
        base.BaseDownloader.set_known_site_map(get_known_site_map())
        self.addCleanup(base.BaseDownloader.clear_cache)
        with TemporaryDirectory() as temporary, patch.object(base, 'local_data', local()):
            params = Params()
            params.base_raw_dir = temporary
            parent = Context(params)
            parent._session = requests.Session()
            self.addCleanup(parent.session.close)
            parent.session.cookies.set('JSESSIONID', 'parent-cookie')
            parent._csrf_token = 'parent-csrf'
            parent._csrf_token_reports = 'parent-report-csrf'
            parent.script_session_id = 'parent-dwr/parent-page'
            parent.script_batch_id = 11
            parent.dwr_session_id = 'parent-dwr'
            # Also cover a populated thread-local inherited by a forked worker.
            base.local_data.ctx = parent
            with patch.object(base, 'setup_logging'):
                base.initialize_process(params, logging.INFO)
            worker = base.get_local_context(params)
            self.assertIsNot(worker, parent)
            children = [
                DwrDownloader(name='probe-levels', base_name='CENTRAL_ADMIN_DEPTS',
                              ctx=parent, csv_filename='levels.csv'),
                OrganizationCoverageDownloader(name='probe-coverage', base_name='ORG_UNIT_COVERAGE',
                              ctx=parent, csv_filename='coverage.csv',
                              organization={'Organization Code': '2078', 'Organization Name': 'Probe'}),
            ]
            for child in children:
                # This is the same serialization used by ProcessPoolExecutor.
                transported = pickle.loads(pickle.dumps(child))
                self.assertEqual(transported.ctx.script_session_id, 'parent-dwr/parent-page')
                with patch.object(DwrCaller, 'call', return_value=[]), patch.object(base, 'get_mem_info'):
                    base.download_task(transported)
                self.assertIs(transported.ctx, worker)
                self.assertIs(transported.captcha_helper.ctx, worker)
                if isinstance(transported, DwrDownloader):
                    self.assertIs(transported.dwr_caller.ctx, worker)
                self.assertTrue(transported.is_done())
                self.assertIs(child.ctx, parent)
            self.assertIsNone(worker._session)
            self.assertIsNone(worker._csrf_token)
            self.assertIsNone(worker.dwr_session_id)
            self.assertEqual(worker.script_session_id, '')
            self.assertEqual(worker.script_batch_id, 0)


if __name__ == '__main__':
    unittest.main()
