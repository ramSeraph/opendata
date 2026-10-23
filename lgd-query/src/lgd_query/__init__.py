"""Public APIs for LGD release metadata, downloads and optional DuckDB access."""

from .metadata import Asset, Dataset, Release, DEFAULT_METADATA_URL, load_manifest, load_release
from .files import download
from .query import connect
from .errors import DatasetUnavailableError, IntegrityError, MetadataError, ObservationDateError

__all__ = [
    'Asset', 'Dataset', 'Release', 'DEFAULT_METADATA_URL', 'load_release', 'load_manifest',
    'download', 'connect', 'DatasetUnavailableError', 'IntegrityError', 'MetadataError',
    'ObservationDateError',
]
