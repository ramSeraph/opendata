"""Dataset-specific SQL helpers over an existing DuckDB connection.

Helpers return native DuckDB relations. They never resolve metadata, download
files, create connections, or import DuckDB until the caller asks for SQL access.
"""

from . import districts, states, subdistricts
from ._catalog import DATASETS, get, required_datasets, sources
from ._prepared import PreparedQuery, prepare

__all__ = ['DATASETS', 'get', 'required_datasets', 'sources', 'PreparedQuery', 'prepare', *DATASETS]


def __getattr__(name):
    if name in DATASETS:
        module = get(name)
        globals()[name] = module
        return module
    raise AttributeError(name)


def __dir__():
    return sorted(set(globals()) | set(DATASETS))
