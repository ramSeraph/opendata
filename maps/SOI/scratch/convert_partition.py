import json
from pathlib import Path

from pmtiles.reader import MmapSource, Reader as PMTilesReader
from pmtiles.tile import (
    tileid_to_zxy,
    deserialize_directory,
    deserialize_header,
)


partition_file = Path('export/pmtiles/partition_info.json')
partition_file_new = Path('export/pmtiles/partition_info_new.json')

def traverse_sizes(get_bytes, header, dir_offset, dir_length):
    entries = deserialize_directory(get_bytes(dir_offset, dir_length))
    for entry in entries:
        if entry.run_length > 0:
            yield entry, entry.length
        else:
            for t in traverse_sizes(
                get_bytes,
                header,
                header["leaf_directory_offset"] + entry.offset,
                entry.length,
            ):
                yield t


def all_tile_sizes(get_bytes):
    header = deserialize_header(get_bytes(0, 127))
    return traverse_sizes(get_bytes, header, header["root_offset"], header["root_length"])

if __name__ == '__main__':
    pmtiles_prefix = 'export/pmtiles/soi-'
    
    p_info = json.loads(partition_file.read_text())
    readers = {}
    for suffix in p_info.keys():
        fname = f'{pmtiles_prefix}{suffix}.pmtiles'
        src = MmapSource(open(fname, 'rb'))
        reader = PMTilesReader(src)
        data = p_info[suffix]
        out = {}
        for (e, size) in all_tile_sizes(src):
            t = tileid_to_zxy(e.tile_id)
            key = f'{t[0]},{t[1]},{t[2]}'
            out[key] = size
        data['tiles'] = out

    partition_file_new.write_text(json.dumps(p_info))
