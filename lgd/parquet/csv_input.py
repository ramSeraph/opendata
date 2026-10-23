"""Read a CSV once and insert bounded, all-string batches into DuckDB."""

from contextlib import contextmanager
import csv
import gzip
import io
from itertools import chain
from pathlib import Path

from .common import sql_identifier


BATCH_ROWS = 8192
BATCH_CHARACTERS = 2 * 1024 * 1024
# Bound individual fields too, while allowing long descriptions. A batch can
# exceed its character target by one record; it never buffers an entire report.
csv.field_size_limit(max(csv.field_size_limit(), 16 * 1024 * 1024))


@contextmanager
def report(source, *, delimiter=None):
    """Accept a path or a borrowed binary stream, including a non-seekable pipe."""
    owned = isinstance(source, (str, Path))
    if owned:
        path = Path(source)
        source = gzip.open(path, 'rb') if path.suffix == '.gz' else path.open('rb')
    text = io.TextIOWrapper(source, encoding='utf-8-sig', newline='')
    try:
        yield CSVReport(text, delimiter=delimiter)
    finally:
        if owned:
            text.close()
        else:
            text.detach()


class CSVReport:
    def __init__(self, text, *, delimiter=None):
        first = text.readline()
        self.delimiter = delimiter or (';' if first.count(';') > first.count(',') else ',')
        self.reader = csv.reader(chain([first], text), delimiter=self.delimiter, strict=True)
        self.headers = next(self.reader, [])

    def rows(self):
        try:
            for row in self.reader:
                if not row:  # Blank physical lines carry no record.
                    continue
                if len(row) != len(self.headers):
                    raise ValueError(f'CSV row at line {self.reader.line_num} has {len(row)} fields; '
                                     f'expected {len(self.headers)}')
                yield row
        except csv.Error as error:
            raise ValueError(f'Invalid CSV at line {self.reader.line_num}: {error}') from error

    def load(self, connection, table, *, observe=None):
        if not self.headers:
            raise ValueError('CSV report has no header')
        fields = ', '.join(f'{sql_identifier(h)} VARCHAR' for h in self.headers)
        connection.execute(f'CREATE OR REPLACE TEMP TABLE {sql_identifier(table)} ({fields})')
        # Parallel UNNEST preserves one tuple per source row, with no inference,
        # null substitution or deduplication. Only one batch crosses Python/SQL.
        insert = f'INSERT INTO {sql_identifier(table)} SELECT ' + ', '.join(
            'unnest(?::VARCHAR[])' for _ in self.headers)
        columns = [[] for _ in self.headers]
        characters = 0
        for row in self.rows():
            if observe is not None:
                observe(row)
            for column, value in zip(columns, row):
                column.append(value)
                characters += len(value)
            if len(columns[0]) >= BATCH_ROWS or characters >= BATCH_CHARACTERS:
                connection.execute(insert, columns)
                columns = [[] for _ in self.headers]
                characters = 0
        if columns[0]:
            connection.execute(insert, columns)
