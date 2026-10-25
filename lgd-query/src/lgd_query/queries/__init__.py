"""Experimental dataset-aware SQL helpers over an existing DuckDB connection.

Arguments, result columns, lookup rules and interpretations of dataset
relationships may change between releases. This includes prepared queries
and reference resolution. See docs/QUERIES.md for the experimental API scope.

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
