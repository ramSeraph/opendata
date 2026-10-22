import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scrape import __main__ as scraper
from scrape.base import Params


class ScrapeStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.status = Path(self.temp.name) / 'status.json'

    def read_status(self):
        return json.loads(self.status.read_text())

    def downloader(self, name, deps=(), children=(), cached=False):
        downloader = Mock()
        downloader.name = name
        downloader.deps = set(deps)
        downloader.is_done.return_value = cached
        downloader.get_child_downloaders.return_value = list(children)
        return downloader

    def test_interruption_preserves_completed_dataset_for_uploader(self):
        downloaders = [self.downloader('FIRST'), self.downloader('NEXT', ['FIRST'])]
        original_wait = scraper.wait
        waits = 0

        def interrupt_second_wait(*args, **kwargs):
            nonlocal waits
            waits += 1
            if waits == 2:
                # The uploader can already use this checkpoint while the
                # rest of the run is unfinished.
                self.assertEqual(self.read_status(), {
                    'done': ['FIRST'], 'error': [], 'left': ['NEXT'],
                })
                raise KeyboardInterrupt('workflow stopped')
            return original_wait(*args, **kwargs)

        with patch.object(scraper, 'get_all_downloaders', return_value=downloaders), \
                patch.object(scraper.CaptchaHelper, 'check_models'), \
                patch.object(scraper, 'download_task'), \
                patch.object(scraper, 'wait', side_effect=interrupt_second_wait):
            with self.assertRaises(KeyboardInterrupt):
                scraper.run(Params(), scraper.Mode.RUN, status_outfile=self.status)
        self.assertEqual(self.read_status(), {
            'done': ['FIRST'], 'error': [], 'left': ['NEXT'],
        })

    def test_failed_atomic_write_keeps_previous_checkpoint(self):
        graph = {'FIRST': set(), 'NEXT': {'FIRST'}}
        for error_type in (OSError, KeyboardInterrupt):
            with self.subTest(error=error_type.__name__):
                scraper.save_run_status(self.status, graph, {'FIRST'}, set())
                previous = self.status.read_bytes()

                def fail_mid_write(value, output):
                    output.write('{"done": [')
                    output.flush()
                    self.assertEqual(self.status.read_bytes(), previous)
                    raise error_type('interrupted write')

                with patch.object(scraper.json, 'dump', side_effect=fail_mid_write):
                    with self.assertRaises(error_type):
                        scraper.save_run_status(self.status, graph, set(graph), set())
                self.assertEqual(self.status.read_bytes(), previous)
                self.assertFalse(self.status.with_suffix('.json.tmp').exists())

    def test_failed_replace_keeps_previous_checkpoint(self):
        graph = {'FIRST': set()}
        scraper.save_run_status(self.status, graph, set(), set())
        with patch.object(Path, 'replace', side_effect=OSError('replace failed')):
            with self.assertRaises(OSError):
                scraper.save_run_status(self.status, graph, {'FIRST'}, set())
        self.assertEqual(self.read_status(), {'done': [], 'error': [], 'left': ['FIRST']})

    def test_new_run_resets_stale_status_and_rechecks_cached_dataset(self):
        self.status.write_text('{"done": ["OLD"], "error": [], "left": []}')
        self.status.with_suffix('.json.tmp').write_text('interrupted old write')
        cached = self.downloader('CACHED', cached=True)

        def check_initial_status(downloader):
            self.assertIs(downloader, cached)
            self.assertEqual(self.read_status(), {
                'done': [], 'error': [], 'left': ['CACHED'],
            })

        with patch.object(scraper, 'download_task', side_effect=check_initial_status):
            scraper.run_on_threads({'CACHED': set()}, {'CACHED': cached},
                                   1, False, Params(), self.status)
        self.assertEqual(self.read_status(), {'done': ['CACHED'], 'error': [], 'left': []})

    def test_parent_is_done_only_after_successful_aggregation(self):
        for failure in (None, 'CHILD', 'PARENT'):
            with self.subTest(failure=failure):
                child = self.downloader('CHILD')
                parent = self.downloader('PARENT', children=[child])
                downstream = self.downloader('DOWNSTREAM', ['PARENT'])
                graph = {'PARENT': set(), 'DOWNSTREAM': {'PARENT'}}
                called = []

                def download(downloader):
                    called.append(downloader.name)
                    if downloader.name in ('CHILD', 'PARENT'):
                        self.assertEqual(self.read_status(), {
                            'done': [], 'error': [], 'left': ['DOWNSTREAM', 'PARENT'],
                        })
                    if downloader.name == failure:
                        raise ValueError('download failed')

                with patch.object(scraper, 'download_task', side_effect=download), \
                        patch.object(scraper, 'logger'):
                    done, errors = scraper.run_on_threads(
                        graph, {'PARENT': parent, 'DOWNSTREAM': downstream},
                        2, False, Params(), self.status)
                if failure:
                    self.assertEqual(done, set())
                    self.assertEqual(errors, {'PARENT'})
                    self.assertEqual(self.read_status(), {
                        'done': [], 'error': ['PARENT'], 'left': ['DOWNSTREAM'],
                    })
                    self.assertNotIn('DOWNSTREAM', called)
                    if failure == 'CHILD':
                        self.assertNotIn('PARENT', called)
                else:
                    self.assertEqual(done, set(graph))
                    self.assertEqual(errors, set())
                    self.assertEqual(self.read_status(), {
                        'done': ['DOWNSTREAM', 'PARENT'], 'error': [], 'left': [],
                    })


if __name__ == '__main__':
    unittest.main()
