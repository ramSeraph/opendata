import unittest
from unittest.mock import Mock

import requests

from scrape.base import Context, Params
from scrape.dwr import DwrCaller, get_fn_call_args


class DwrStringTests(unittest.TestCase):
    def decode(self, literal):
        response = requests.Response()
        response.status_code = 200
        response.headers['Content-Type'] = 'text/javascript;charset=UTF-8'
        response._content = (
            "dwr.engine.remote.handleCallback('0','0',[{name:" + literal + '}]);'
        ).encode()
        ctx = Context(Params())
        ctx._session = Mock()
        ctx.session.post.return_value = response
        caller = DwrCaller(ctx=ctx, base_url='https://example.test')
        result = caller.make_request('Department', 'levels', '/report')
        return get_fn_call_args('dwr.engine.remote.handleCallback', result)[2][0]['name']

    def test_javascript_escaped_slash_matches_browser_value(self):
        for literal in [r'"O\/o District Assistant Officer"',
                        r"'O\/o District Assistant Officer'"]:
            with self.subTest(literal=literal):
                self.assertEqual(self.decode(literal), 'O/o District Assistant Officer')

    def test_literal_backslashes_and_other_escapes_are_preserved(self):
        for literal, expected in [(r'"O/o"', 'O/o'),
                                  (r'"\\/"', '\\/'),
                                  (r'"\\\/"', '\\/'),
                                  (r'"C:\\office"', 'C:\\office'),
                                  (r'"A\nB\tC"', 'A\nB\tC'),
                                  (r'"\u0915\u093e\/Office"', 'का/Office'),
                                  (r'"say \"O\/o\""', 'say "O/o"')]:
            with self.subTest(literal=literal):
                self.assertEqual(self.decode(literal), expected)


if __name__ == '__main__':
    unittest.main()
