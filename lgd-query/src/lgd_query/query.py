"""DuckDB access layered on resolved datasets and optional verified downloads."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Iterable, Mapping

from .files import download
from .metadata import Dataset

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


def connect(datasets: Iterable[Dataset], *, cache_dir: str | os.PathLike | None = None,
            config: Mapping | None = None, timeout: float = 30,
            retries: int = 2) -> DuckDBPyConnection:
    """Open an in-memory DuckDB connection with a view named for each dataset.

    Without cache_dir, DuckDB reads immutable remote URLs using HTTP range
    requests. With cache_dir, download() verifies complete local files first.
    Close the connection or use it as a context manager. No index is refetched.
    timeout/retries apply to downloads; DuckDB controls remote query transport.
    """
    datasets = tuple(datasets)
    if not datasets or any(not isinstance(d, Dataset) for d in datasets):
        raise ValueError('Pass one or more resolved Dataset objects')
    if len({d.name for d in datasets}) != len(datasets):
        raise ValueError('Dataset view names must be unique')
    for dataset in datasets:
        dataset.require_available()
    try:
        import duckdb
    except ImportError as error:
        raise ImportError('SQL access requires: pip install "lgd-query[duckdb]"') from error
    connection = duckdb.connect(config=dict(config or {}))
    try:
        for dataset in datasets:
            path = (str(download(dataset, cache_dir, timeout=timeout, retries=retries))
                    if cache_dir is not None else dataset.parquet.url)
            connection.read_parquet(path).create_view(dataset.name, replace=False)
        return connection
    except BaseException:
        connection.close()
        raise
