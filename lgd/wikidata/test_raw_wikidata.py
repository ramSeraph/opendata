import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from raw_wikidata import WikidataClient, download_query, read_records, write_records


def response(data=None, status=200, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(data).encode() if data is not None else b'Too many requests'
    result.headers.update(headers or {})
    return result


def entity(qid):
    return {'id': qid, 'type': 'item', 'claims': {}, 'labels': {'en': {'language': 'en', 'value': qid}}}


class ClientTests(unittest.TestCase):
    def client(self, *responses, **kwargs):
        client = WikidataClient(interval=0, **kwargs)
        client.session.get = Mock(side_effect=responses)
        return client

    def test_raw_claims_and_languages_survive_without_remote_resolution(self):
        item = entity('Q1')
        item['claims']['P3896'] = [{'mainsnak': {'datatype': 'geo-shape', 'datavalue': {'value': 'Data:India/Manipur.map'}}}]
        item['labels']['hi'] = {'language': 'hi', 'value': 'मणिपुर'}
        client = self.client(response({'entities': {'Q1': item}}))
        self.assertEqual(client.entities(['Q1']), {'Q1': item})
        self.assertEqual(client.session.get.call_count, 1)
        self.assertEqual(client.session.get.call_args.args[0], 'https://www.wikidata.org/w/api.php')
        self.assertEqual(client.session.get.call_args.kwargs['params']['maxlag'], 5)

    @patch('raw_wikidata.time.sleep')
    def test_rate_limit_honors_retry_after_even_with_non_json_body(self, sleep):
        client = self.client(response(status=429, headers={'Retry-After': '65'}), response({'entities': {'Q1': entity('Q1')}}))
        client.entities(['Q1'])
        sleep.assert_called_once_with(65)

    @patch('raw_wikidata.time.sleep')
    def test_api_maxlag_is_retried_and_remains_enabled(self, sleep):
        client = self.client(response({'error': {'code': 'maxlag', 'info': 'Lagged'}}), response({'entities': {'Q1': entity('Q1')}}))
        client.entities(['Q1'])
        sleep.assert_called_once_with(5)
        for call in client.session.get.call_args_list:
            self.assertEqual(call.kwargs['params']['maxlag'], 5)

    @patch('raw_wikidata.time.sleep')
    def test_lag_retry_exhaustion_is_an_error(self, sleep):
        client = self.client(*[response({'error': {'code': 'maxlag', 'info': 'Lagged'}}) for _ in range(2)], attempts=2)
        with self.assertRaisesRegex(RuntimeError, 'after 2 attempts: maxlag'):
            client.entities(['Q1'])

    @patch('raw_wikidata.time.sleep')
    def test_transport_timeout_is_retried(self, sleep):
        client = self.client(requests.Timeout('timeout'), response({'entities': {'Q1': entity('Q1')}}))
        self.assertEqual(client.entities(['Q1'])['Q1']['id'], 'Q1')

    def test_non_retryable_error_fails_immediately(self):
        client = self.client(response({'error': {'code': 'badvalue', 'info': 'Invalid ID'}}))
        with self.assertRaisesRegex(RuntimeError, 'badvalue'):
            client.entities(['Q1'])
        self.assertEqual(client.session.get.call_count, 1)

    def test_incomplete_entity_response_fails(self):
        client = self.client(response({'entities': {'Q1': entity('Q1')}}))
        with self.assertRaisesRegex(ValueError, 'Q2'):
            client.entities(['Q1', 'Q2'])

    def test_redirected_labels_are_resolved(self):
        client = self.client(response({'redirects': [{'from': 'Q1', 'to': 'Q2'}], 'entities': {'Q2': entity('Q2')}}))
        self.assertEqual(client.entities(['Q1'], props='labels', languages='en')['Q1']['id'], 'Q2')

    def test_batch_limit_and_interactive_setting(self):
        client = self.client(response({'entities': {'Q1': entity('Q1')}}), maxlag=None)
        with self.assertRaises(ValueError):
            client.entities(['Q1'] * 51)
        client.entities(['Q1'])
        self.assertNotIn('maxlag', client.session.get.call_args.kwargs['params'])


class CheckpointTests(unittest.TestCase):
    def test_failure_preserves_old_output_and_retry_fetches_only_missing_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'entities.jsonl'
            write_records(path, {'Q1': entity('Q1')})
            original = path.read_bytes()
            ids = [f'Q{i}' for i in range(1, 56)]
            source = Mock()
            source.query_ids.return_value = ids
            source.entities.side_effect = [dict((qid, entity(qid)) for qid in ids[1:51]), RuntimeError('interrupted')]
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                download_query('query', path, source=source)
            self.assertEqual(path.read_bytes(), original)
            parts = path.with_name(path.name + '.parts')
            self.assertEqual(len(list(parts.glob('*.jsonl'))), 1)
            (parts / 'incomplete.jsonl.tmp').write_text('{"id":')
            retry = Mock()
            retry.query_ids.return_value = ids
            retry.entities.side_effect = lambda batch: {qid: entity(qid) for qid in batch}
            self.assertEqual(download_query('query', path, source=retry), 55)
            retry.entities.assert_called_once_with(ids[51:])
            self.assertEqual(read_records(path), {qid: entity(qid) for qid in ids})

    def test_write_failure_does_not_replace_published_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'entities.jsonl'
            write_records(path, {'Q1': entity('Q1')})
            original = path.read_bytes()
            with self.assertRaises(TypeError):
                write_records(path, {'Q2': object()})
            self.assertEqual(path.read_bytes(), original)

    def test_empty_query_does_not_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'entities.jsonl'
            write_records(path, {'Q1': entity('Q1')})
            source = Mock()
            source.query_ids.return_value = []
            with self.assertRaisesRegex(ValueError, 'empty download'):
                download_query('query', path, source=source)
            self.assertEqual(read_records(path), {'Q1': entity('Q1')})


class LabelTests(unittest.TestCase):
    def test_label_prefers_english_then_multilingual(self):
        import common
        cases = [
            ({'en': {'value': 'English name'}, 'mul': {'value': 'Shared name'}}, 'English name'),
            ({'mul': {'value': 'Nagaon district'}}, 'Nagaon district'),
            ({'hi': {'value': 'नगाँव'}}, 'NA'),
            ({}, 'NA'),
        ]
        for labels, expected in cases:
            with self.subTest(labels=labels):
                self.assertEqual(common.get_label({'labels': labels}), expected)
        self.assertEqual(common.get_label({}), 'NA')

    def test_multilingual_label_does_not_need_transliteration(self):
        import common
        item = {'labels': {'mul': {'value': 'Nagaon district'}}}
        self.assertEqual(common.get_label_translit(item), 'Nagaon district')

    def test_downloaded_labels_are_reused_without_api_calls(self):
        import common
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                Path('data').mkdir()
                write_records(Path('data/states.jsonl'), {'Q1': entity('Q1')})
                with patch.object(common, 'page_cache', None), patch.object(common.client, 'entities') as fetch:
                    self.assertEqual(common.get_entry_from_wd_id('1'), {'id': 'Q1', 'label': 'Q1'})
                    self.assertEqual(common.get_entry_from_wd_id(1), {'id': 'Q1', 'label': 'Q1'})
                    fetch.assert_not_called()
            finally:
                os.chdir(previous)

    def test_downloaded_multilingual_label_replaces_cached_missing_label(self):
        import common
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                Path('data').mkdir()
                item = entity('Q1')
                item['labels'] = {'mul': {'language': 'mul', 'value': 'Name'}}
                write_records(Path('data/states.jsonl'), {'Q1': item})
                Path('data/cache.jsonl').write_text(json.dumps({'id': 1, 'data': {'id': 'Q1', 'label': 'NA'}}) + '\n')
                with patch.object(common, 'page_cache', None), patch.object(common.client, 'entities') as fetch:
                    self.assertEqual(common.get_entry_from_wd_id(1)['label'], 'Name')
                    fetch.assert_not_called()
            finally:
                os.chdir(previous)

    def test_uncached_and_previously_missing_labels_request_multilingual_fallback(self):
        import common
        for cached in (False, True):
            with self.subTest(cached=cached), tempfile.TemporaryDirectory() as directory:
                previous = Path.cwd()
                try:
                    os.chdir(directory)
                    Path('data').mkdir()
                    if cached:
                        Path('data/cache.jsonl').write_text(json.dumps({'id': 1, 'data': {'id': 'Q1', 'label': 'NA'}}) + '\n')
                    item = {'labels': {'mul': {'value': 'Shared name'}}}
                    with patch.object(common, 'page_cache', None), patch.object(common.client, 'entities', return_value={'Q1': item}) as fetch:
                        self.assertEqual(common.get_entry_from_wd_id(1)['label'], 'Shared name')
                        self.assertEqual(common.get_entry_from_wd_id(1)['label'], 'Shared name')
                        fetch.assert_called_once_with(['Q1'], props='labels', languages='en|mul')
                    with patch.object(common, 'page_cache', None), patch.object(common.client, 'entities') as fetch:
                        self.assertEqual(common.get_entry_from_wd_id(1)['label'], 'Shared name')
                        fetch.assert_not_called()
                finally:
                    os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
