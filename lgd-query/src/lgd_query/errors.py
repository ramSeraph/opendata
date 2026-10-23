"""Errors exposed by the reader APIs."""


class MetadataError(ValueError):
    """The discovery index or dataset manifest does not match its contract."""


class IntegrityError(ValueError):
    """Downloaded bytes differ from their advertised size or SHA-256."""


class DatasetUnavailableError(LookupError):
    """A known dataset has no published Parquet file."""


class ObservationDateError(ValueError):
    """The published report does not have the requested observation date."""
