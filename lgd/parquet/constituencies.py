"""Validate constituency report serials and recognize timestamp footers."""

import re

from .csv_input import report


DATASETS = ('parliament_constituencies', 'assembly_constituencies')
TIMESTAMP = re.compile(
    r'(?:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?|'
    r'[A-Z][a-z]{2} \d{1,2}, \d{4},? \d{1,2}:\d{2} [AP]M)')


def source_layout(path):
    """Validate serials/footers and report missing prefix rows without filling them."""
    with report(path, delimiter=',') as source:
        layout = Layout(source.headers)
        for row in source.rows():
            layout.observe(row)
    return layout.result()


class Layout:
    """Validate report order during ingestion, without a second CSV pass."""

    def __init__(self, headers):
        if not {'S.No.', 'State Code'} <= set(headers):
            raise ValueError('Constituency report lacks serial/state columns')
        self.serial_index, self.state_index = headers.index('S.No.'), headers.index('State Code')
        self.first = self.last = self.first_state = None
        self.footers = 0

    def observe(self, row):
        serial = row[self.serial_index]
        if TIMESTAMP.fullmatch(serial) and not any(v for i, v in enumerate(row) if i != self.serial_index):
            self.footers += 1
            return
        if not re.fullmatch(r'[0-9]+', serial) or self.footers:
            raise ValueError(f'Unexpected constituency row: serial {serial!r}')
        serial = int(serial)
        if self.first is None:
            self.first, self.first_state = serial, row[self.state_index]
            if self.first not in (1, 81):
                raise ValueError(f'Unreviewed constituency prefix: starts at {self.first}')
        elif serial != self.last + 1:
            raise ValueError(f'Constituency serial gap: {self.last} followed by {serial}')
        self.last = serial

    def result(self):
        if self.first is None:
            raise ValueError('Constituency report has no numbered rows')
        return {'source_first_serial': self.first, 'source_last_serial': self.last,
                'missing_prefix_rows': self.first - 1, 'ignored_footer_rows': self.footers,
                'partial_state_codes': [self.first_state] if self.first > 1 else []}
