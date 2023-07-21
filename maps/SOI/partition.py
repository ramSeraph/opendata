import json
from pathlib import Path

import mercantile
from pprint import pprint
from pmtiles.tile import zxy_to_tileid, tileid_to_zxy, TileType, Compression
from pmtiles.writer import Writer, write

from tile_sources import (
    DiskSource,
    DiskAndPartitionedPMTilesSource,
    MissingTileError
)

# account for some sqlite overhead
DELTA = 5 * 1024 * 1024
# github release limit
size_limit_bytes = (2 * 1024 * 1024 * 1024) - DELTA
# cloudflare cache size limit
#size_limit_bytes = (512 * 1024 * 1024) - DELTA
max_level = 14
min_level = 2

SOI_ATTRIBUTION = '<a href="https://onlinemaps.surveyofindia.gov.in/FreeMapSpecification.aspx" target="_blank">1:50000 Open Series Maps</a> © <a href="https://www.surveyofindia.gov.in/pages/copyright-policy" target="_blank">Survey Of India</a>'


def get_layer_info(l, reader):
    tiles = {}
    total_size = 0
    for tile, size in reader.for_all_z(l):
        tiles[tile] = size
        total_size += size
    return total_size, tiles



def get_buckets(sizes, tiles):
    buckets = []
    bucket_tiles = []

    max_x = max(sizes.keys())
    min_x = min(sizes.keys())

    cb = (min_x, min_x)
    cs = 0
    bts = {}
    for i in range(min_x, max_x + 1):
        if i not in sizes:
            continue
        if cs > size_limit_bytes:
            buckets.append(cb)
            bucket_tiles.append(bts)
            cb = (i,i)
            cs = 0
            bts = {}
        cs += sizes[i]
        bts.update(tiles[i])
        cb = (cb[0], i)
    buckets.append(cb)
    bucket_tiles.append(bts)
    return buckets, bucket_tiles

missing_tiles = set()

def get_stripes(l, reader):

    tiles = {}
    sizes = {}
    #max_x = min_x = max_y = min_y = None
    missed_count = 0
    print(f'striping from level {l}')
    count = 0
    for tile, size in reader.for_all_z(l):
        count += 1
        #if count % 1000 == 0:
        #    print(f'handled {count} tiles')
        to_add = [(tile, size)]
        for clevel in range(l + 1, max_level + 1):
            children = mercantile.children(tile, zoom=clevel)
            for ctile in children:
                try:
                    csize = reader.get_tile_size(ctile)
                    to_add.append((ctile, size))
                except MissingTileError:
                    missing_tiles.add(ctile)
                    continue
                #size += csize

        for t, s in to_add:
            if tile.x not in tiles:
                tiles[tile.x] = {}
            tiles[tile.x][t] = size
            if tile.x not in sizes:
                sizes[tile.x] = 0
            sizes[tile.x] += s
    print(f'{len(missing_tiles)=}')
    return sizes, tiles


def get_top_slice(reader):
    print('getting top slice')
    size_till_now = 0
    tiles = {}
    for l in range(min_level, max_level + 1):
        lsize, ltiles = get_layer_info(l, reader)
        size_till_now += lsize
        print(f'{l=}, {lsize=}, {size_till_now=}, {size_limit_bytes=}')
        tiles.update(ltiles)
        if size_till_now > size_limit_bytes:
            return l - 1, tiles
    return max_level, tiles

def save_partition_info(p_info, partition_file):
    out = {}
    for p_name, p_data in p_info.items():
        tiles_new = { f'{t.z},{t.x},{t.y}':size for t, size in p_data['tiles'].items() }
        p_data['tiles'] = tiles_new

    partition_file.parent.mkdir(exist_ok=True, parents=True)
    partition_file.write_text(json.dumps(p_info))


def get_bounds(tiles):

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


def get_partition_info(reader):
    if to_partition_file.exists():
        partition_info = json.loads(to_partition_file.read_text())
        for suffix, data in partition_info.items():
            tdata = {}
            for k, size in data['tiles'].items():
                kps = k.split(',')
                tile = mercantile.Tile(
                    x=int(kps[1]),
                    y=int(kps[2]),
                    z=int(kps[0]),
                )
                tdata[tile] = size
            data['tiles'] = tdata
        return partition_info

    partition_info = {}
    top_slice_max_level, top_slice_tiles = get_top_slice(reader)

    top_slice_bounds = get_bounds(top_slice_tiles.keys())

    partition_name = f'z{min_level}-{top_slice_max_level}'
    partition_info[partition_name] = {
        "tiles": top_slice_tiles,
        "min_zoom": min_level,
        "max_zoom": top_slice_max_level,
        "bounds": top_slice_bounds
    }
    if top_slice_max_level == max_level:
        print('no more slicing required')
        return partition_info


    from_level = top_slice_max_level + 1
    stripe_sizes, stripe_tiles = get_stripes(from_level, reader)
    buckets, bucket_tiles = get_buckets(stripe_sizes, stripe_tiles)

    for i,bucket in enumerate(buckets):
        partition_name = f'z{from_level}-{max_level}-part{i}'
        partition_info[partition_name] = {
            'tiles': bucket_tiles[i],
            "min_zoom": from_level,
            "max_zoom": max_level,
            "bounds": get_bounds(bucket_tiles[i].keys()),
        }
    return partition_info


def create_pmtiles(partition_info, reader):
    mosaic_data = {}
    to_pmtiles_prefix = 'staging/pmtiles/soi-'
    for suffix, data in partition_info.items():
        out_pmtiles_file = f'{to_pmtiles_prefix}{suffix}.pmtiles'
        Path(out_pmtiles_file).parent.mkdir(exist_ok=True, parents=True)
        with write(out_pmtiles_file) as writer:
            curr_z = None
            for t in data['tiles'].keys():
                if curr_z is None or curr_z < t.z:
                    max_lat = min_lat = max_lon = min_lon = None
                    curr_z = t.z
                t_bounds = mercantile.bounds(t)
                if max_lat is None or t_bounds.north > max_lat:
                    max_lat = t_bounds.north
                if min_lat is None or t_bounds.south < min_lat:
                    min_lat = t_bounds.south
                if max_lon is None or t_bounds.east > max_lon:
                    max_lon = t_bounds.east
                if min_lon is None or t_bounds.west < min_lon:
                    min_lon = t_bounds.west
                t_data = reader.get_tile_data(t)
                t_id = zxy_to_tileid(t.z, t.x, t.y)
                writer.write_tile(t_id, t_data)
            metadata = { 'attribution': SOI_ATTRIBUTION }
            header = {
                "tile_type": TileType.WEBP,
                "tile_compression": Compression.NONE,
                "min_lon_e7": int(min_lon * 10000000),
                "min_lat_e7": int(min_lat * 10000000),
                "max_lon_e7": int(max_lon * 10000000),
                "max_lat_e7": int(max_lat * 10000000),
                "center_zoom": 0,
                "center_lon_e7": int(10000000 * (min_lon + max_lon)/2),
                "center_lat_e7": int(10000000 * (min_lat + max_lat)/2),
            }
            m_key = f'./{Path(out_pmtiles_file).name}'
            header['tile_type'] = header['tile_type'].value
            header['tile_compression'] = header['tile_compression'].value
            mosaic_data[m_key] = header
            writer.finalize(header, metadata)
    return mosaic_data


if __name__ == '__main__':

    to_partition_file = Path('staging/pmtiles/partition_info.json')
    #reader = DiskSource('export/tiles')
    reader = DiskAndPartitionedPMTilesSource('staging/tiles', 'export/pmtiles/soi-', 'export/pmtiles/partition_info.json')

    partition_info = get_partition_info(reader)
    if not to_partition_file.exists():
        save_partition_info(partition_info, to_partition_file)

    mosaic_data = create_pmtiles(partition_info, reader)
    Path('staging/pmtiles/mosaic.json').write_text(json.dumps(mosaic_data))

