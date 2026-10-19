"""Read Wikidata JSON without resolving claims into remote page objects."""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests


API = 'https://www.wikidata.org/w/api.php'
SPARQL = 'https://query.wikidata.org/sparql'
USER_AGENT = 'LGD-Wikidata-Sync/0.1 (https://github.com/ramSeraph/opendata)'


class WikidataClient:
    def __init__(self, *, maxlag=5, interval=1.0, attempts=10):
        # Daily runs can wait through a short service outage: the default
        # backoff spans about 11 minutes; Retry-After can extend these waits.
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        self.maxlag = maxlag
        self.interval = interval
        self.attempts = attempts
        self.last_request = 0.0
        self.requests = 0
        self.bytes = 0

    def request(self, url, params):
        for attempt in range(self.attempts):
            delay = self.interval - (time.monotonic() - self.last_request)
            if delay > 0:
                time.sleep(delay)
            self.last_request = time.monotonic()
            self.requests += 1
            response = None
            try:
                response = self.session.get(url, params=params, timeout=(10, 90))
                self.bytes += len(response.content)
                if response.status_code in (429, 500, 502, 503, 504):
                    reason = f'HTTP {response.status_code}'
                else:
                    response.raise_for_status()
                    data = response.json()
                    error = data.get('error')
                    if error is None:
                        return data
                    reason = f"{error.get('code')}: {error.get('info', '')}"
                    if error.get('code') not in ('maxlag', 'ratelimited', 'readonly'):
                        raise RuntimeError(reason)
            except (requests.ConnectionError, requests.Timeout) as error:
                reason = str(error)

            if attempt + 1 == self.attempts:
                raise RuntimeError(f'Wikidata request failed after {self.attempts} attempts: {reason}')
            wait = min(5 * 2 ** attempt, 120)
            if response is not None:
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        wait = max(wait, float(retry_after))
                    except ValueError:
                        retry_at = parsedate_to_datetime(retry_after)
                        wait = max(wait, (retry_at - datetime.now(timezone.utc)).total_seconds())
            print(f'{reason}; retrying in {wait:.0f}s', flush=True)
            time.sleep(wait)

    def query_ids(self, query):
        data = self.request(SPARQL, {'query': query, 'format': 'json'})
        ids = {row['item']['value'].rsplit('/', 1)[-1]
               for row in data['results']['bindings']}
        if any(not re.fullmatch(r'Q[1-9][0-9]*', qid) for qid in ids):
            raise ValueError('SPARQL returned an invalid item ID')
        return sorted(ids, key=lambda qid: int(qid[1:]))

    def entities(self, ids, *, props=None, languages=None):
        if not 1 <= len(ids) <= 50:
            raise ValueError('Entity batches must contain 1 to 50 IDs')
        params = {'action': 'wbgetentities', 'ids': '|'.join(ids), 'format': 'json'}
        if self.maxlag is not None:
            params['maxlag'] = self.maxlag
        if props is not None:
            params['props'] = props
        if languages is not None:
            params['languages'] = languages
        data = self.request(API, params)
        entities = data['entities']
        redirects = {row['from']: row['to'] for row in data.get('redirects', [])}
        result = {}
        for qid in ids:
            resolved = qid
            seen = set()
            while resolved in redirects:
                if resolved in seen:
                    raise ValueError(f'Redirect cycle for {qid}')
                seen.add(resolved)
                resolved = redirects[resolved]
            entity = entities.get(resolved)
            if not entity or 'missing' in entity:
                raise ValueError(f'Wikidata did not return a live entity for {qid}')
            result[qid] = entity
        return result


# Only foreground local tests opt out of maxlag. Scheduled runs retain maxlag=5.
client = WikidataClient(maxlag=None if os.environ.get('LGD_WIKIDATA_INTERACTIVE') == '1' else 5)


def read_records(path):
    records = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                records[row['id']] = row['data']
    return records


def write_records(path, records):
    """Publish a checkpoint or output only after writing every record."""
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as stream:
        for qid, entity in records.items():
            stream.write(json.dumps({'id': qid, 'data': entity}) + '\n')
    temporary.replace(path)


def download_query(query, filename, *, source=None):
    source = source or client
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = path.with_name(path.name + '.parts')
    parts.mkdir(exist_ok=True)
    expected = source.query_ids(query)
    if not expected:
        raise ValueError(f'No entities returned for {filename}; refusing to publish an empty download')
    records = read_records(path)
    for part in sorted(parts.glob('*.jsonl')):
        records.update(read_records(part))
    pending = [qid for qid in expected if qid not in records]
    print(f'{filename}: {len(expected)} entities, {len(pending)} to download', flush=True)
    for offset in range(0, len(pending), 50):
        ids = pending[offset:offset + 50]
        batch = source.entities(ids)
        digest = hashlib.sha256('|'.join(ids).encode()).hexdigest()[:20]
        write_records(parts / f'{digest}.jsonl', batch)
        records.update(batch)
        print(f'{filename}: {len(expected) - len(pending) + offset + len(ids)}/{len(expected)}', flush=True)
    write_records(path, {qid: records[qid] for qid in expected})
    return len(expected)
