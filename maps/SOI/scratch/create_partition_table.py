import json
from pathlib import Path

import mercantile
from pmtiles.reader import MmapSource, Reader as PMTilesReader, all_tiles

def key_to_tile(k):
    kps = k.split(',')
    tile = mercantile.Tile(
        x=int(kps[1]),
        y=int(kps[2]),
        z=int(kps[0]),
    )
    return tile


def get_bounds(tiles_dict):

    keys = tiles_dict.keys()
    tiles = [ key_to_tile(k) for k in keys ]

    bounds = [ mercantile.bounds(t) for t in tiles ]

    max_x = bounds[0].east
    min_x = bounds[0].west
    max_y = bounds[0].north
    min_y = bounds[0].south
    for b in bounds:
        if b.east > max_x:
            max_x = b.east

        if b.west < min_x:
            min_x = b.west

        if b.north > max_y:
            max_y = b.north

        if b.south < min_y:
            min_y = b.south

    return (min_y, min_x, max_y, max_x)


prefix = 'export/pmtiles/soi-'

partition_fname = 'export/pmtiles/partition_info.json'

partition_info = {}

for file in Path('./').glob(f'{prefix}*.pmtiles'):
    print(f'reading {file=}')
    suffix = str(file)[len(prefix):][:-len('.pmtiles')]

    src = MmapSource(open(file, 'rb'))
    reader = PMTilesReader(src)

    min_zoom = 50
    max_zoom = -1

    tiles = {}
    for t, t_data in all_tiles(reader.get_bytes):
        min_zoom = min(t[0], min_zoom)
        max_zoom = max(t[0], max_zoom)
        key  = f'{t[0]},{t[1]},{t[2]}'
        tiles[key] = len(t_data)

    bounds = get_bounds(tiles)

    partition_info[suffix] = {
        'tiles': tiles,
        'bounds': bounds,
        'min_zoom': min_zoom,
        'max_zoom': max_zoom
    }

Path(partition_fname).write_text(json.dumps(partition_info))
