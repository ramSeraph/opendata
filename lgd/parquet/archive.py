"""Stream selected 7z members with extraction and content-integrity checks."""

from contextlib import contextmanager
import hashlib
import io
import subprocess
import tempfile
import zlib


def members(path):
    listing = subprocess.run(['7z', 'l', '-slt', '--', str(path)],
                             check=True, capture_output=True, text=True).stdout
    sections = listing.split('----------\n', 1)
    if len(sections) != 2:
        raise ValueError(f'Cannot read archive listing: {path}')
    entries = []
    for block in sections[1].strip().split('\n\n'):
        fields = dict(line.split(' = ', 1) for line in block.splitlines() if ' = ' in line)
        if 'Path' not in fields:
            continue
        name = fields['Path']
        if '/' in name or '\\' in name or not name.endswith('.csv'):
            raise ValueError(f'Unexpected archive member: {name}')
        size = int(fields['Size'])
        crc = int(fields['CRC'], 16) if fields.get('CRC') else (0 if size == 0 else None)
        if size < 0 or crc is None:
            raise ValueError(f'Missing/invalid archive size or checksum: {name}')
        entries.append((name, size, crc))
    if not entries or len({name for name, _, _ in entries}) != len(entries):
        raise ValueError(f'Empty archive or duplicate members: {path}')
    return entries


class DigestReader(io.RawIOBase):
    """Hash the bytes as a consumer reads them, without seeking or staging."""

    def __init__(self, source, expected_size=None):
        super().__init__()
        self.source = source
        self.expected_size = expected_size
        self.digest = hashlib.sha256()
        self.crc = self.size = 0
        self.eof = False

    def readable(self):
        return True

    def readinto(self, buffer):
        count = self.source.readinto(buffer)
        if count == 0:
            self.eof = True
        if count:
            self.size += count
            if self.expected_size is not None and self.size > self.expected_size:
                raise ValueError('Unexpected extra archive data')
            data = memoryview(buffer)[:count]
            self.digest.update(data)
            self.crc = zlib.crc32(data, self.crc)
        return count


@contextmanager
def stream_member(archive, entry):
    """Reject truncation, extra bytes, bad CRCs and extractor errors before return."""
    member, size, expected_crc = entry
    # File-backed stderr cannot fill a pipe and deadlock the extractor.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(['7z', 'x', '-so', '-spd', '--', str(archive), member],
                                   stdout=subprocess.PIPE, stderr=errors)
        checked = DigestReader(process.stdout, size)
        try:
            with io.BufferedReader(checked) as stream:
                yield stream, checked
            if not checked.eof:
                raise ValueError(f'Archive member was not fully consumed: {member}')
            code = process.wait()
            if code != 0 or checked.size != size or checked.crc != expected_crc:
                errors.seek(0)
                diagnostic = errors.read(2000).decode(errors='replace').strip()
                raise ValueError(f'Incomplete/corrupt archive extraction for {member}: {diagnostic}')
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdout.close()
