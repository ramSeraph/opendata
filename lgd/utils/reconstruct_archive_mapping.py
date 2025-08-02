# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "py7zr",
#     "urllib3",
# ]
# ///


import py7zr
import urllib3
import io
import csv
import json

class HTTPRangeReader(io.RawIOBase):
    def __init__(self, url):
        self.url = url
        self.http = urllib3.PoolManager()
        self._length = self._get_content_length()
        self._pos = 0

    def _get_content_length(self):
        r = self.http.request('HEAD', self.url)
        return int(r.headers['Content-Length'])

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self._pos = offset
        elif whence == io.SEEK_CUR:
            self._pos += offset
        elif whence == io.SEEK_END:
            self._pos = self._length + offset
        return self._pos

    def tell(self):
        return self._pos

    def read(self, size=-1):
        if size == -1:
            end = self._length - 1
        else:
            end = min(self._pos + size - 1, self._length - 1)

        if self._pos > end:
            return b""

        headers = {'Range': f'bytes={self._pos}-{end}'}
        r = self.http.request('GET', self.url, headers=headers)
        data = r.data
        self._pos += len(data)
        return data

    def readable(self):
        return True

    def seekable(self):
        return True

    def readinto(self, b):
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

def get_file_list_from_archive(url):

    out = []
    remote_file = HTTPRangeReader(url)

    with py7zr.SevenZipFile(remote_file, mode='r') as archive:
        file_list = archive.getnames()
        print("Files in archive:")
        for f in file_list:
            out.append(f)
    return out

by_key = {}
with open("archive_listing_files.csv", 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        url = row['url']
        print(f"Processing archive: {url}")
        file_list = get_file_list_from_archive(url)
        for file in file_list:
            parts = file.split('.')
            key = parts[0]
            date = parts[1]
            if key not in by_key:
                by_key[key] = []
            by_key[key].append(date)

with open("archive_mapping.json", 'w') as f:
    json.dump(by_key, f)
