import os
import re
import json

import time
import os.path
import subprocess

from pathlib import Path


import mercantile

from osgeo_utils.gdal2tiles import main as gdal2tiles_main
from osgeo_utils.gdal2tiles import create_overview_tile, TileJobInfo, GDAL2Tiles


from tile_sources import PartitionedPMTilesSource, MissingTileError

INDEX_FILE_NAME = 'data/index.geojson'


orig_pmtiles_dir = Path('export/pmtiles')
tiles_dir = Path('staging/tiles')
tiffs_dir = Path('staging/gtiffs')

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def run_external(cmd):
    print(f'running cmd - {cmd}')
    start = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    print(f'STDOUT: {res.stdout}')
    print(f'STDERR: {res.stderr}')
    print(f'command took {end - start} secs to run')
    if res.returncode != 0:
        raise Exception(f'command {cmd} failed')


def convert_paths_in_vrt(vrt_file):
    # <SourceFilename relativeToVRT="1">40M_15.tif</SourceFilename>
    vrt_dirname = str(vrt_file.resolve().parent)
    vrt_text = vrt_file.read_text()
    replaced = re.sub(
        r'<SourceFilename relativeToVRT="1">(.*)</SourceFilename>',
        rf'<SourceFilename relativeToVRT="0">{vrt_dirname}/\1</SourceFilename>',
        vrt_text
    )
    vrt_file.write_text(replaced)

    
def create_base_tiles(inp_file, output_dir, zoom_levels):
    print('start tiling')
    os.environ['GDAL_CACHEMAX'] = '2048'
    os.environ['GDAL_MAX_DATASET_POOL_SIZE'] = '5000'
    os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'TRUE'
    #os.environ['VRT_SHARED_SOURCE'] = '1'
    #os.environ['GTIFF_VIRTUAL_MEM_IO'] = 'TRUE'
    gdal2tiles_main(['gdal2tiles.py',
                     '-r', 'antialias',
                     '--verbose',
                     '-w', 'none',
                     '--exclude', 
                     '--resume', 
                     '--xyz', 
                     '--processes=8', 
                     '-z', zoom_levels,
                     '--tiledriver', 'WEBP',
                     '--webp-quality', '50',
                     inp_file, output_dir])



pmtiles_reader = None
def get_pmtiles_reader():
    global pmtiles_reader
    if pmtiles_reader is None:
        pmtiles_reader = PartitionedPMTilesSource(f'{orig_pmtiles_dir}/soi-',
                                                  f'{orig_pmtiles_dir}/soi.partition_info.json')
    return pmtiles_reader


def pull_from_pmtiles(file):
    reader = get_pmtiles_reader()
    fname = str(file)
    pieces = fname.split('/')
    tile = mercantile.Tile(x=int(pieces[-2]),
                           y=int(pieces[-1].replace('.webp', '')),
                           z=int(pieces[-3]))
    try:
        t_data = reader.get_tile_data(tile)
    except MissingTileError:
        return
    file.parent.mkdir(exist_ok=True, parents=True)
    file.write_bytes(t_data)


def get_tile_file(tile):
    return f'{tiles_dir}/{tile.z}/{tile.x}/{tile.y}.webp'

def get_tile_file_orig(tile):
    return f'{orig_tiles_dir}/{tile.z}/{tile.x}/{tile.y}.webp'

def check_sheets(sheets_to_pull):
    for sheet_no in sheets_to_pull:
        to = tiffs_dir.joinpath(f'{sheet_no}.tif')
        if not to.exists():
            raise Exception(f'missing file {to}')

def copy_tiles_over(tiles_to_pull):
    for tile in tiles_to_pull:
        to = Path(get_tile_file(tile))
        if to.exists():
            continue
        pull_from_pmtiles(to)


def create_upper_tiles(tiles_to_create):
    options = AttrDict({
        'resume': True,
        'verbose': False,
        'quiet': False,
        'xyz': True,
        'exclude_transparent': True,
        'profile': 'mercator',
        'resampling': 'antialias',
        'tiledriver': 'WEBP',
        'webp_quality': 50,
        'webp_lossless': False
    })
    tile_job_info = TileJobInfo(
        tile_driver='WEBP',
        nb_data_bands=3,
        tile_size=256,
        tile_extension='webp',
        kml=False
    )

    for tile in tiles_to_create:
        ctiles = mercantile.children(tile)
        tiles_dir.joinpath(str(tile.z), str(tile.x)).mkdir(parents=True, exist_ok=True)
        base_tile_group = [ (t.x, GDAL2Tiles.getYTile(t.y, t.z, options)) for t in ctiles ]
        #print(f'{tile=}, {base_tile_group=}')
        create_overview_tile(z + 1, output_folder=str(tiles_dir), tile_job_info=tile_job_info, options=options, base_tiles=base_tile_group)
 

def get_sheet_data():
    index_file = Path(INDEX_FILE_NAME)
    if not index_file.exists():
        raise Exception(F'missing index file at {INDEX_FILE_NAME}')

    index_data = json.loads(index_file.read_text())

    sheets_to_box = {}
    for f in index_data['features']:
        sheet_no = f['properties']['EVEREST_SH'].replace('/', '_')
        box = f['geometry']['coordinates'][0][:-1]
        sheets_to_box[sheet_no] = box

    return sheets_to_box


def get_base_tile_sheet_mappings(sheets_to_box, base_zoom):
    sheets_to_base_tiles = {}
    base_tiles_to_sheets = {}

    for sheet_no, box in sheets_to_box.items():
        tiles = set(mercantile.tiles(box[0][0], box[2][1], box[2][0], box[0][1], [base_zoom])) 
        sheets_to_base_tiles[sheet_no] = tiles
        for tile in tiles:
            if tile not in base_tiles_to_sheets:
                base_tiles_to_sheets[tile] = set()
            base_tiles_to_sheets[tile].add(sheet_no)

    return sheets_to_base_tiles, base_tiles_to_sheets


def delete_unwanted_tiles(tiles_to_keep, z):
    delete_count = 0
    for file in tiles_dir.glob(f'{z}/*/*.webp'):
        y = int(file.name[:-5])
        x = int(file.parent.name)
            
        disk_tile = mercantile.Tile(z=z, x=x, y=y)
        if disk_tile not in tiles_to_keep:
            #print(f'deleting {disk_tile}')
            file.unlink()
            delete_count += 1
    print(f'deleted {delete_count} files at level {z}')


def create_vrt_file(sheets):
    vrt_file = Path(f'{tiffs_dir}/combined.vrt')
    if vrt_file.exists():
        return vrt_file
    tiff_list = [ tiffs_dir.joinpath(f'{p_sheet}.tif').resolve() for p_sheet in sheets ]
    tiff_list = [ str(f) for f in tiff_list if f.exists() ]

    tiff_list_str = ' '.join(tiff_list)

    run_external(f'gdalbuildvrt {vrt_file} {tiff_list_str}')
    convert_paths_in_vrt(vrt_file)

    return vrt_file


if __name__ == '__main__':

    import sys
    if len(sys.argv) < 3:
        print('ERROR: needs atleast 2 arguments')
        print(f'USAGE: {sys.argv[0]} <retile_file> <full_tiff_list_file> <sheet_list_output_file>')
        exit(1)

    retile_list_file = sys.argv[1]
    retile_sheets = Path(retile_list_file).read_text().split('\n')
    retile_sheets = set([ r.strip() for r in retile_sheets if r.strip() != '' ])

    full_tiff_list_file = sys.argv[2] 
    available_sheets = Path(full_tiff_list_file).read_text().split('\n')
    available_sheets = set([ r.strip() for r in available_sheets if r.strip() != '' ])

    sheets_to_pull_outfile = None
    if len(sys.argv) > 3:
        sheets_to_pull_outfile = sys.argv[3]

    tiles_dir.mkdir(parents=True, exist_ok=True)
    tiffs_dir.mkdir(parents=True, exist_ok=True)

    zmin = 0
    zmax = 14

    print('getting base tiles to sheet mapping')
    sheets_to_box = get_sheet_data()
    sheets_to_base_tiles, base_tiles_to_sheets = get_base_tile_sheet_mappings(sheets_to_box, zmax)

    all_affected_tiles = set()

    print('calculating sheets to pull')
    affected_base_tiles = set()
    for sheet_no in retile_sheets:
        affected_base_tiles.update(sheets_to_base_tiles[sheet_no])
    all_affected_tiles.update(affected_base_tiles)

    sheets_to_pull = set()
    for tile in affected_base_tiles:
        to_add = base_tiles_to_sheets[tile]
        for sheet in to_add:
            if sheet in available_sheets:
                sheets_to_pull.add(sheet)

    print(f'{sheets_to_pull=}')
    if sheets_to_pull_outfile is not None:
        Path(sheets_to_pull_outfile).write_text('\n'.join(sheets_to_pull) + '\n')
        exit(0)

    print('check the sheets availability')
    check_sheets(sheets_to_pull)

    print('creating vrt file from sheets involved')
    vrt_file = create_vrt_file(sheets_to_pull)

    print('creating tiles for base zoom with a vrt')
    create_base_tiles(f'{vrt_file}', str(tiles_dir), f'{zmax}')

    print('deleting unwanted base tiles')
    delete_unwanted_tiles(affected_base_tiles, zmax)

    prev_affected_tiles = affected_base_tiles
    for z in range(zmax-1, zmin-1, -1):
        print(f'handling level {z}')

        curr_affected_tiles = set()
        for tile in prev_affected_tiles:
            curr_affected_tiles.add(mercantile.parent(tile))
        all_affected_tiles.update(curr_affected_tiles)

        child_tiles_to_pull = set()
        for ptile in curr_affected_tiles:
            for ctile in mercantile.children(ptile):
                if ctile not in prev_affected_tiles:
                    child_tiles_to_pull.add(ctile)

        print('copying additional child tiles required for curr level')
        copy_tiles_over(child_tiles_to_pull)

        print('creating tiles for current level')
        create_upper_tiles(curr_affected_tiles)

        print('removing unwanted child tiles')
        delete_unwanted_tiles(prev_affected_tiles, z+1)

        prev_affected_tiles = curr_affected_tiles

    print('All Done!!!')



