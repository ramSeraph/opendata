"""Structured report-validation errors shared with downstream consumers."""


class InputRejected(ValueError):
    """Validation failure with structured, bounded affected-key evidence."""

    def __init__(self, message, *, affected_keys):
        super().__init__(message)
        self.affected_keys = affected_keys
