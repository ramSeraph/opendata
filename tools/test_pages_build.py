"""Check the Pages data contract against the existing public reader."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_pages import publish_data, Release


class PagesDataTests(unittest.TestCase):
    def test_every_available_file_and_manifest_is_rehosted_and_verifiable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            datasets, collected = {}, {}
            for name, representation in [('states', 'snapshot'), ('transactions', 'events')]:
                content = b'PAR1' + name.encode() + b'PAR1'
                path = root / f'{name}.parquet'
                path.write_bytes(content)
                daily = {'file': {'url': f'https://github.com/example/repo/releases/download/data/{name}.parquet',
                                  'size': len(content), 'sha256': hashlib.sha256(content).hexdigest()},
                         'rows': 2, 'observed_on': '2026-10-25' if representation == 'snapshot' else None,
                         'uploaded_at': '2026-10-25T00:00:00+00:00'}
                entry = {'daily': daily, 'identity': name, 'representation': representation,
                         'coverage': None, 'outcome': {'status': 'updated'},
                         'manifest': {'url': f'https://github.com/example/repo/releases/download/data/{name}.json',
                                      'size': 1, 'sha256': 'a' * 64}}
                datasets[name] = entry
                collected[name] = (path, {'kind': 'lgd-daily-parquet', 'format_version': 1,
                                         'dataset': name, 'schema': [], **{k: v for k, v in entry.items() if k not in ('manifest', 'outcome')}})
            datasets['unavailable'] = {'outcome': {'status': 'unavailable', 'reason': 'No report'}, 'daily': None, 'manifest': None}
            release = Release.from_dict({'kind': 'lgd-daily-parquet', 'format_version': 1,
                                        'generation': 'test', 'published_at': '2026-10-25T00:00:00+00:00',
                                        'immutable_url': 'https://github.com/example/repo/releases/download/data/index.json',
                                        'repository': 'example/repo', 'datasets': datasets})
            public, reports = publish_data(release, collected, root / 'site', 'https://example.github.io/opendata')
            parsed = Release.from_dict(public)
            self.assertEqual(list(parsed.datasets), list(release.datasets))
            self.assertFalse(parsed.datasets['unavailable'].available)
            for name in ('states', 'transactions'):
                dataset = parsed.dataset(name)
                self.assertTrue(dataset.parquet.url.startswith('https://example.github.io/opendata/lgd/data/'))
                self.assertTrue(dataset.manifest.url.startswith('https://example.github.io/opendata/lgd/data/'))
                data_dir = root / 'site/lgd/data'
                dataset.parquet.verify((data_dir / dataset.parquet.url.rsplit('/', 1)[1]).read_bytes())
                content = (data_dir / dataset.manifest.url.rsplit('/', 1)[1]).read_bytes()
                dataset.manifest.verify(content)
                manifest = json.loads(content)
                self.assertEqual(manifest['daily'], dataset.metadata['daily'])
                self.assertEqual(manifest['identity'], dataset.identity)
                self.assertTrue(release.dataset(name).parquet.url.startswith('https://github.com/'))
            self.assertIsNone(parsed.dataset('transactions').observed_on)
            self.assertEqual(reports['states']['date'], '2026-10-25')
            self.assertEqual(json.loads((root / 'site/lgd/data/metadata.json').read_text()), public)


if __name__ == '__main__':
    unittest.main()
