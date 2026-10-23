"""Anonymous HTTP transport shared by metadata and file downloads."""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .errors import MetadataError


MAX_METADATA_BYTES = 8 * 1024 * 1024


def http_url(value):
    if not isinstance(value, str):
        raise MetadataError('Expected an HTTP(S) URL')
    try:
        parts = urlsplit(value)
        # Accessing port performs validation; urlsplit alone accepts bad ports.
        parts.port
        valid = (parts.scheme in ('https', 'http') and parts.hostname and
                 parts.username is None and parts.password is None and not parts.fragment and
                 not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value))
    except ValueError as error:
        raise MetadataError(f'Invalid public HTTP(S) URL: {value!r}') from error
    if not valid:
        raise MetadataError(f'Invalid public HTTP(S) URL: {value!r}')
    return value


def open_url(url, *, timeout=30, retries=2):
    http_url(url)
    if timeout <= 0 or type(retries) is not int or retries < 0:
        raise ValueError('timeout must be positive and retries a nonnegative integer')
    request = Request(url, headers={'User-Agent': 'lgd-query', 'Accept-Encoding': 'identity'})
    for attempt in range(retries + 1):
        try:
            return urlopen(request, timeout=timeout)
        except HTTPError as error:
            # metadata.json can briefly disappear during release replacement.
            error.close()
            if error.code not in (404, 408, 429, 500, 502, 503, 504) or attempt == retries:
                raise
        except (URLError, TimeoutError):
            if attempt == retries:
                raise
        time.sleep(0.5 * 2**attempt)


def read_json(url, *, asset=None, timeout=30, retries=2):
    if asset is not None and asset.size > MAX_METADATA_BYTES:
        raise MetadataError('Manifest exceeds the metadata size limit')
    with open_url(url, timeout=timeout, retries=retries) as response:
        content = response.read(MAX_METADATA_BYTES + 1)
    if len(content) > MAX_METADATA_BYTES:
        raise MetadataError('Response exceeds the metadata size limit')
    if asset is not None:
        asset.verify(content)
    try:
        result = json.loads(content)
    except (ValueError, UnicodeError) as error:
        raise MetadataError(f'Invalid JSON metadata: {url}') from error
    if not isinstance(result, dict):
        raise MetadataError('Metadata must be a JSON object')
    return result
