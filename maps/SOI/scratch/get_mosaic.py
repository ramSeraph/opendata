import json
from pathlib import Path

import mercantile
from pmtiles.tile import TileType, Compression

SOI_ATTRIBUTION = '<a href="https://onlinemaps.surveyofindia.gov.in/FreeMapSpecification.aspx" target="_blank">1:50000 Open Series Maps</a> © <a href="https://www.surveyofindia.gov.in/pages/copyright-policy" target="_blank">Survey Of India</a>'
def get_mosaic(partition_info):
    mosaic_data = {}
    to_pmtiles_prefix = 'export/pmtiles/soi-'
    for suffix, data in partition_info.items():
        out_pmtiles_file = f'{to_pmtiles_prefix}{suffix}.pmtiles'
        #Path(out_pmtiles_file).parent.mkdir(exist_ok=True, parents=True)
        curr_z = None
        max_zoom = min_zoom = None
        for tile in data['tiles']:
            tile = tile.split(',')
            tile = [ int(p) for p in tile ]
            t = mercantile.Tile(x=tile[1], y=tile[2], z=tile[0])
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
            if min_zoom is None or t.z < min_zoom:
                min_zoom = t.z
            if max_zoom is None or t.z > max_zoom:
                max_zoom = t.z
        metadata = { 'attribution': SOI_ATTRIBUTION }
        header = {
            "tile_type": TileType.WEBP,
            "tile_compression": Compression.NONE,
            "min_lon_e7": int(min_lon * 10000000),
            "min_lat_e7": int(min_lat * 10000000),
            "max_lon_e7": int(max_lon * 10000000),
            "max_lat_e7": int(max_lat * 10000000),
            "min_zoom": min_zoom,
            "max_zoom": max_zoom,
            "center_zoom": 0,
            "center_lon_e7": int(10000000 * (min_lon + max_lon)/2),
            "center_lat_e7": int(10000000 * (min_lat + max_lat)/2),
        }
        m_key = f'../{Path(out_pmtiles_file).name}'
        header['tile_type'] = header['tile_type'].value
        header['tile_compression'] = header['tile_compression'].value
        mosaic_data[m_key] = { 'header': header, 'metadata': metadata }
    return mosaic_data

partition_info = json.loads(Path('export/pmtiles/partition_info.json').read_text())
mosaic_data = get_mosaic(partition_info)
Path('export/pmtiles/mosaic.json').write_text(json.dumps(mosaic_data))
