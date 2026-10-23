"""Publishing retry checks use the same bytes on PyPI and GitHub."""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError


spec = importlib.util.spec_from_file_location('check_dist', Path(__file__).resolve().parents[1]/'tools/check_dist.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class PublicationRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = []
        for name, content in [('lgd_query-0.1.0-py3-none-any.whl', b'wheel'),
                              ('lgd_query-0.1.0.tar.gz', b'source')]:
            (self.root/name).write_bytes(content)
            self.files.append(dict(filename=name, size=len(content),
                                   digests=dict(sha256=hashlib.sha256(content).hexdigest())))

    def check(self, files, *, complete=False):
        with patch.object(release, 'urlopen', return_value=io.BytesIO(json.dumps({'urls': files}).encode())):
            return release.check_published(self.root, '0.1.0', require_complete=complete)

    def test_initial_upload_and_identical_partial_retry(self):
        error = HTTPError('https://pypi.org/', 404, 'Not found', {}, None)
        with patch.object(release, 'urlopen', side_effect=error):
            self.assertEqual(release.check_published(self.root, '0.1.0'), 0)
            with self.assertRaisesRegex(ValueError, 'not yet visible'):
                release.check_published(self.root, '0.1.0', require_complete=True)
        self.assertEqual(self.check(self.files[:1]), 1)
        with self.assertRaisesRegex(ValueError, 'Not all'):
            self.check(self.files[:1], complete=True)
        self.assertEqual(self.check(self.files, complete=True), 2)

    def test_different_bytes_cannot_be_silently_skipped_or_released(self):
        (self.root/self.files[0]['filename']).write_bytes(b'other')
        for complete in (False, True):
            with self.assertRaisesRegex(ValueError, 'different bytes'):
                self.check(self.files, complete=complete)

    def test_other_artifacts_and_network_errors_do_not_mean_missing_version(self):
        self.files[0]['filename'] = 'unexpected.whl'
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            self.check(self.files)
        for error in (HTTPError('https://pypi.org/', 503, 'Busy', {}, None), URLError('offline')):
            with patch.object(release, 'urlopen', side_effect=error), self.assertRaises(type(error)):
                release.check_published(self.root, '0.1.0')


if __name__ == '__main__':
    unittest.main()
