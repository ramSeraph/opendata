"""Dataset-specific SQL helpers over an existing DuckDB connection.

Helpers return native DuckDB relations. They never resolve metadata, download
files, create connections, or import DuckDB until the caller asks for SQL access.
"""

from . import districts, states, subdistricts
from ._catalog import DATASETS, get, required_datasets, sources

__all__ = ['DATASETS', 'get', 'required_datasets', 'sources', *DATASETS]


def __getattr__(name):
    if name in DATASETS:
        module = get(name)
        globals()[name] = module
        return module
    raise AttributeError(name)
