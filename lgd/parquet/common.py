"""Small, dependency-free helpers shared by LGD report readers."""

import hashlib
import re
from datetime import datetime


def header_key(value):
    return re.sub(r'[\s().-]', '', value).casefold()


def sql_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def sql_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def file_hash(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def filename_date(path, dataset='villages'):
    match = re.fullmatch(rf'{re.escape(dataset)}\.(\d{{2}}[A-Za-z]{{3}}\d{{4}})\.csv', path.name)
    if not match:
        raise ValueError(f'Expected {dataset}.DDMonYYYY.csv: {path}')
    return datetime.strptime(match[1], '%d%b%Y').date()
