"""Resolve the daily release index without importing DuckDB or downloader code."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
import re
from types import MappingProxyType
from typing import Any, Mapping

from ._http import http_url, read_json
from .errors import DatasetUnavailableError, IntegrityError, MetadataError, ObservationDateError


DEFAULT_METADATA_URL = ('https://github.com/ramSeraph/opendata/releases/download/'
                        'lgd-parquet-latest/metadata.json')


def _require(condition, message):
    if not condition:
        raise MetadataError(message)


def _object(value, label):
    _require(isinstance(value, dict), f'{label} must be an object')
    return value


def _text(value, label):
    _require(isinstance(value, str) and bool(value), f'Missing/invalid {label}')
    return value


def _date(value):
    try:
        result = date.fromisoformat(value)
        if result.isoformat() == value:
            return result
    except (TypeError, ValueError):
        pass
    raise MetadataError(f'Expected a YYYY-MM-DD observation date: {value!r}')


def _timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is not None:
            return result
    except (AttributeError, TypeError, ValueError):
        pass
    raise MetadataError(f'Expected a timestamp with a timezone: {value!r}')


def _contract(document):
    _object(document, 'Metadata')
    _require(document.get('kind') == 'lgd-daily-parquet' and
             type(document.get('format_version')) is int and document['format_version'] == 1,
             'Unsupported daily Parquet metadata kind/version')


@dataclass(frozen=True)
class Asset:
    """An immutable file reference advertised by the release metadata."""

    url: str
    size: int
    sha256: str

    def __post_init__(self):
        http_url(self.url)
        _require(type(self.size) is int and self.size > 0, 'Invalid asset size')
        _require(isinstance(self.sha256, str) and re.fullmatch('[a-f0-9]{64}', self.sha256),
                 'Invalid asset SHA-256')

    @classmethod
    def from_dict(cls, value: dict) -> Asset:
        value = _object(value, 'Asset')
        return cls(value.get('url'), value.get('size'), value.get('sha256'))

    def verify(self, content: bytes) -> None:
        if len(content) != self.size or hashlib.sha256(content).hexdigest() != self.sha256:
            raise IntegrityError(f'Content differs from advertised size/SHA-256: {self.url}')


@dataclass(frozen=True)
class Dataset:
    """One dataset in a pinned index, including its actual date and outcome."""

    name: str
    status: str
    reason: str | None
    representation: str | None
    observed_on: date | None
    uploaded_at: datetime | None
    rows: int | None
    parquet: Asset | None
    manifest: Asset | None
    identity: str | None
    _entry: dict = field(repr=False, compare=False)

    @property
    def available(self) -> bool:
        """True even if a failed update retained an older, usable file."""
        return self.parquet is not None

    @property
    def metadata(self) -> dict:
        """A detached copy of the dataset's original index entry."""
        return deepcopy(self._entry)

    @property
    def coverage(self) -> dict | None:
        """Event date/collection coverage; snapshot reports normally have none."""
        return deepcopy(self._entry.get('coverage'))

    def require_available(self) -> Dataset:
        if not self.available:
            raise DatasetUnavailableError(f'{self.name}: {self.reason or self.status}')
        return self

    @classmethod
    def _parse(cls, name, entry):
        _require(isinstance(name, str) and re.fullmatch('[a-z][a-z0-9_]*', name),
                 f'Invalid dataset name: {name!r}')
        entry = deepcopy(_object(entry, f'{name} entry'))
        outcome = _object(entry.get('outcome'), f'{name} outcome')
        status = outcome.get('status')
        _require(status in ('updated', 'unchanged', 'unavailable', 'blocked', 'failed'),
                 f'{name}: unknown publication outcome')
        reason = outcome.get('reason')
        _require(reason is None or isinstance(reason, str), f'{name}: invalid failure reason')
        if entry.get('daily') is None:
            _require(entry.get('manifest') is None and status in ('unavailable', 'blocked', 'failed'),
                     f'{name}: published dataset has no daily file')
            return cls(name, status, reason, None, None, None, None, None, None, None, entry)
        daily = _object(entry['daily'], f'{name} daily')
        representation = entry.get('representation')
        _require(representation in ('snapshot', 'events'), f'{name}: unknown representation')
        observed = daily.get('observed_on')
        if representation == 'snapshot':
            observed = _date(observed)
        else:
            _require(observed is None, f'{name}: event rows must not invent an observation date')
        rows = daily.get('rows')
        _require(type(rows) is int and rows >= 0, f'{name}: invalid row count')
        coverage = entry.get('coverage')
        _require(coverage is None or isinstance(coverage, dict), f'{name}: invalid coverage')
        return cls(name, status, reason, representation, observed, _timestamp(daily.get('uploaded_at')),
                   rows, Asset.from_dict(daily.get('file')), Asset.from_dict(entry.get('manifest')),
                   _text(entry.get('identity'), f'{name} identity'), entry)


@dataclass(frozen=True)
class Release:
    """A single metadata generation; accessing it never refetches latest."""

    generation: str
    published_at: datetime
    immutable_url: str
    repository: str
    datasets: Mapping[str, Dataset]
    source_url: str | None
    _document: dict = field(repr=False, compare=False)

    @classmethod
    def from_dict(cls, document: dict, *, source_url: str | None = None) -> Release:
        """Resolve a previously saved JSON index without network requests."""
        _contract(document)
        document = deepcopy(document)
        entries = _object(document.get('datasets'), 'datasets')
        datasets = MappingProxyType({name: Dataset._parse(name, entry) for name, entry in entries.items()})
        return cls(_text(document.get('generation'), 'generation'),
                   _timestamp(document.get('published_at')), http_url(document.get('immutable_url')),
                   _text(document.get('repository'), 'repository'), datasets, source_url, document)

    @property
    def metadata(self) -> dict:
        """A detached JSON-serializable index, suitable for saving and reopening."""
        return deepcopy(self._document)

    def dataset(self, name: str, *, observed_on: date | str | None = None) -> Dataset:
        """Resolve a usable dataset, optionally requiring an exact source date.

        The date requirement never falls back to an older report and does not
        perform a historical lookup. Cumulative events have no observation date.
        """
        try:
            result = self.datasets[name].require_available()
        except KeyError:
            raise KeyError(f'Unknown dataset: {name}') from None
        if observed_on is not None:
            expected = observed_on if type(observed_on) is date else _date(observed_on)
            if result.observed_on != expected:
                raise ObservationDateError(f'{name}: requested {expected}, published observation '
                                           f'is {result.observed_on} (outcome: {result.status})')
        return result


def load_release(url: str = DEFAULT_METADATA_URL, *, timeout: float = 30, retries: int = 2) -> Release:
    """Fetch the current index once, or pin an explicitly supplied immutable URL."""
    return Release.from_dict(read_json(url, timeout=timeout, retries=retries), source_url=url)


def load_manifest(dataset: Dataset, *, timeout: float = 30, retries: int = 2) -> dict[str, Any]:
    """Fetch schema/source details, verify bytes, and match them to the pinned index."""
    dataset.require_available()
    ref = dataset.manifest
    manifest = read_json(ref.url, asset=ref, timeout=timeout, retries=retries)
    _contract(manifest)
    _require(manifest.get('dataset') == dataset.name, 'Manifest belongs to another dataset')
    for key in ('identity', 'representation', 'daily', 'coverage'):
        _require(manifest.get(key) == dataset._entry.get(key), f'Manifest differs from index: {key}')
    return manifest
