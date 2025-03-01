# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pmtiles",
# ]
# ///

import json
import sqlite3
from pathlib import Path

from pmtiles.tile import TileType
from pmtiles.reader import MmapSource, all_tiles

dir = Path('staging/pmtiles')

out_mbtiles_file = 'staging/soi.mbtiles'

def get_metadata(mosaic_data):
    ch = {}
    cm = {}
    for k, item in mosaic_data.items():
        h = item['header']
        # TODO: not generic, max and min zoom can from metadata
        if 'max_zoom' not in ch or ch['max_zoom'] < h['max_zoom']:
            ch['max_zoom'] = h['max_zoom']
        if 'min_zoom' not in ch or ch['min_zoom'] > h['min_zoom']:
            ch['min_zoom'] = h['min_zoom']
        if 'max_lat_e7' not in ch or ch['max_lat_e7'] < h['max_lat_e7']:
            ch['max_lat_e7'] = h['max_lat_e7']
        if 'min_lat_e7' not in ch or ch['min_lat_e7'] > h['min_lat_e7']:
            ch['min_lat_e7'] = h['min_lat_e7']
        if 'max_lon_e7' not in ch or ch['max_lon_e7'] < h['max_lon_e7']:
            ch['max_lon_e7'] = h['max_lon_e7']
        if 'min_lon_e7' not in ch or ch['min_lon_e7'] > h['min_lon_e7']:
            ch['min_lon_e7'] = h['min_lon_e7']
        ch['tile_type'] = h['tile_type']
    cm['maxzoom'] = ch['max_zoom']
    cm['minzoom'] = ch['min_zoom']
    max_lat = ch['max_lat_e7'] / 10000000 
    min_lat = ch['min_lat_e7'] / 10000000
    max_lon = ch['max_lon_e7'] / 10000000
    min_lon = ch['min_lon_e7'] / 10000000
    cm['bounds'] = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    center_lat = (max_lat + min_lat) / 2
    center_lon = (max_lon + min_lon) / 2 
    center_zoom = 0 # TODO: not generic
    cm['center'] = f"{center_lon},{center_lat},{center_zoom}"
    tile_type = ch['tile_type']
    if tile_type == TileType.MVT.value:
        cm["format"] = "pbf"
    elif tile_type == TileType.PNG.value:
        cm["format"] = "png"
    elif tile_type == TileType.JPEG.value:
        cm["format"] = "jpeg"
    elif tile_type == TileType.WEBP.value:
        cm["format"] = "webp"
    elif tile_type == TileType.AVIF.value:
        cm["format"] = "avif"
    cm["version"] = "2"
    cm["type"] = "baselayer"
    #TODO: to be more generic there are a few more fields to look at
    return cm

def optimize_cursor(cursor):
    cursor.execute("""PRAGMA synchronous=0""")
    cursor.execute("""PRAGMA locking_mode=EXCLUSIVE""")
    cursor.execute("""PRAGMA journal_mode=DELETE""")


def get_mbtiles_conn():
    conn = sqlite3.connect(out_mbtiles_file)
    cursor = conn.cursor()
    optimize_cursor(cursor)
    return conn, cursor


def initialize_tables(cursor, metadata):
    cursor.execute("CREATE TABLE metadata (name text, value text);")
    cursor.execute(
        "CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob);"
    )
    for k,v in metadata.items():
        cursor.execute("INSERT INTO metadata VALUES(?,?)", (k, v))

def add_to_mbtiles(pmtiles_fname, cursor):
    print(f'adding {pmtiles_fname} to mbtiles')
    with open(pmtiles_fname, "r+b") as f:
        source = MmapSource(f)

        for zxy, tile_data in all_tiles(source):
            flipped_y = (1 << zxy[0]) - 1 - zxy[2]
            cursor.execute(
                "INSERT INTO tiles VALUES(?,?,?,?)",
                (zxy[0], zxy[1], flipped_y, tile_data),
            )



def finalize_mbtiles(conn, cursor):
    cursor.execute(
        "CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row);"
    )
    conn.commit()
    cursor.execute("""ANALYZE;""")

    conn.close()



if __name__ == '__main__':
    mosaic_file = dir / 'mosaic.json'
    mosaic_data = json.loads(mosaic_file.read_text())
    metadata = get_metadata(mosaic_data)
    conn, cursor = get_mbtiles_conn()
    initialize_tables(cursor, metadata)
    for k in mosaic_data.keys():
        pmtiles_file = dir / Path(k).name
        add_to_mbtiles(str(pmtiles_file), cursor)

    finalize_mbtiles(conn, cursor)
