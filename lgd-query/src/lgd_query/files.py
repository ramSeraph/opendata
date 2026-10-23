"""Verified downloads, independent of DuckDB and metadata fetching."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

from ._http import open_url
from .errors import IntegrityError
from .metadata import Dataset


def _digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download(dataset: Dataset, directory: str | os.PathLike, *,
             timeout: float = 30, retries: int = 2) -> Path:
    """Return a size/SHA-256 verified Parquet file in the requested directory.

    Names contain the full content hash. Valid files are reused; corrupt cached
    files are replaced only after a complete replacement passes verification.
    Interrupted transfers never become final cache entries.
    """
    dataset.require_available()
    asset = dataset.parquet
    directory = Path(directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f'{dataset.name}.{asset.sha256}.parquet'
    if (destination.exists() and destination.stat().st_size == asset.size and
            _digest(destination) == asset.sha256):
        return destination
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=f'.{dataset.name}.',
                                         suffix='.tmp', delete=False) as target:
            temporary = Path(target.name)
            digest, size = hashlib.sha256(), 0
            with open_url(asset.url, timeout=timeout, retries=retries) as response:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > asset.size:
                        raise IntegrityError(f'{dataset.name}: download exceeds advertised size')
                    digest.update(chunk)
                    target.write(chunk)
            if size != asset.size or digest.hexdigest() != asset.sha256:
                raise IntegrityError(f'{dataset.name}: download differs from advertised size/SHA-256')
            target.flush()
            os.fsync(target.fileno())
        temporary.replace(destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
