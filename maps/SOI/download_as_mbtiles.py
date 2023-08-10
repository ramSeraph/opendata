import json
import shutil
import sqlite3
import requests

from pathlib import Path

from pmtiles.reader import Reader, MmapSource, all_tiles
from pmtiles.tile import TileType, Compression

mosaic_url = 'https://github.com/ramSeraph/opendata/releases/download/soi-latest/mosaic.json'
mosaic_file = 'mosaic.json'

out_mbtiles_file = 'soi.mbtiles'
tracker_fname = 'tracker.txt'

# heavily copied from https://github.com/protomaps/PMTiles/blob/main/python/pmtiles/convert.py
# and https://github.com/mapbox/mbutil/blob/master/mbutil/util.py

def download_file(url, fname):
    print(f'downloading {url} to {fname}')
    resp = requests.get(url, stream=True)
    with open(fname, 'wb') as f:
        for data in resp.iter_content(chunk_size=4096):
            f.write(data)


def get_mosaic():
    if not Path(mosaic_file).exists():
        download_file(mosaic_url, mosaic_file)
    with open(mosaic_file, 'r') as f:
        return json.load(f)


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


def finalize_mbtiles(conn, cursor):
    cursor.execute(
        "CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row);"
    )
    conn.commit()
    cursor.execute("""ANALYZE;""")

    conn.close()


def add_to_mbtiles(pmtiles_fname, cursor):
    print(f'adding {pmtiles_fname} to mbtiles')
    with open(pmtiles_fname, "r+b") as f:
        source = MmapSource(f)
        reader = Reader(source)

        for zxy, tile_data in all_tiles(source):
            flipped_y = (1 << zxy[0]) - 1 - zxy[2]
            cursor.execute(
                "INSERT INTO tiles VALUES(?,?,?,?)",
                (zxy[0], zxy[1], flipped_y, tile_data),
            )


def optimize_cursor(cursor):
    cursor.execute("""PRAGMA synchronous=0""")
    cursor.execute("""PRAGMA locking_mode=EXCLUSIVE""")
    cursor.execute("""PRAGMA journal_mode=DELETE""")


def initialize_tables(cursor, metadata):
    cursor.execute("CREATE TABLE metadata (name text, value text);")
    cursor.execute(
        "CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob);"
    )
    for k,v in metadata.items():
        cursor.execute("INSERT INTO metadata VALUES(?,?)", (k, v))



def get_mbtiles_conn():
    conn = sqlite3.connect(out_mbtiles_file)
    cursor = conn.cursor()
    optimize_cursor(cursor)
    return conn, cursor


def get_pmtiles_url(k):
    if k.startswith('../'):
        return mosaic_url + '/' + k
    return k


def init_tracker():
    if not Path(tracker_fname).exists():
        Path(tracker_fname).write_text("")


def stage_done(stage):
    txt = Path(tracker_fname).read_text()
    done_stages = txt.split('\n')
    if stage in done_stages:
        return True
    return False


def mark_done(stage):
    with open(tracker_fname, 'a') as f:
        f.write(stage)
        f.write('\n')


if __name__ == '__main__':
    #Path(tracker_fname).parent.mkdir(parents=True, exist_ok=True)
    mosaic_data = get_mosaic()
    metadata = get_metadata(mosaic_data)
    conn, cursor = get_mbtiles_conn()
    init_tracker()
    if not stage_done('table_init'):
        initialize_tables(cursor, metadata)
        mark_done('table_init')
    for k in mosaic_data.keys():
        pmtiles_url = get_pmtiles_url(k)
        if stage_done(k):
            continue
        pmtiles_fname = pmtiles_url.split('/')[-1]
        download_file(pmtiles_url, pmtiles_fname)
        add_to_mbtiles(pmtiles_fname, cursor)
        mark_done(k)
        Path(pmtiles_fname).unlink()

    finalize_mbtiles(conn, cursor)
    Path(tracker_fname).unlink()
    Path(mosaic_file).unlink()
    print('done')
    
