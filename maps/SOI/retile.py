import os
import json
import shutil

import time
import os.path
import subprocess

from pathlib import Path
from multiprocessing import Pool
from functools import partial

import mercantile
from osgeo import gdal

from gdal2tiles import main as gdal2tiles_main
from gdal2tiles import create_overview_tile, TileJobInfo, GDAL2Tiles

OVERWRITE=False

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

def get_file_info(file_names):
    info = {}
    for file_name in file_names:
        info[file_name] = os.path.getmtime(file_name)
    return info

def get_updated_files(new_info, old_info):
    updated = []
    for file_name in new_info.keys():
        if file_name not in old_info:
            updated.append(file_name)
        else:
            prev_update_time = old_info[file_name]
            cur_update_time = new_info[file_name]
            if cur_update_time > prev_update_time:
                updated.append(file_name)
    return updated

def file_to_tiles(file_name):
    z_min = 2
    z_max = 15
    ds = gdal.Open(file_name)
    if ds is None:
        raise Exception("Could not open file!")
    gt = ds.GetGeoTransform()

    # Get the geographic coordinates of the file's left top and right bottom 
    lt = mercantile.lnglat(gt[0], gt[3])
    rb = mercantile.lnglat(gt[0] + (ds.RasterXSize * gt[1]), 
                           gt[3] + (ds.RasterYSize * gt[5]))

    # Use the coordinates and z levels we create a list of tiles to generate
    tiles = set(mercantile.tiles(lt.lng, rb.lat, rb.lng, lt.lat, 
                                  range(z_min, z_max + 1)))
    #ds.close()
    ds = None
    return tiles

def get_affected_tile_set(file_list):
    affected_tiles = set()
    for filename in file_list:
        affected_tiles.update(file_to_tiles(filename))
    return affected_tiles


def get_sheets_to_basetile_mapping(ndex_data):
    sheets_to_base_tiles = {}
    base_tiles_to_sheets = {}
    for f in index_data['features']:
        sheet_no = f['properties']['EVEREST_SH'].replace('/', '_')
        box = f['geometry']['coordinates'][0][:-1]
        tiles = set(mercantile.tiles(box[0][0], box[2][1], box[2][0], box[0][1], [z_max])) 
        sheets_to_base_tiles[sheet_no] = tiles
        for tile in tiles:
            if tile not in base_tiles_to_sheets:
                base_tiles_to_sheets[tile] = set()
            base_tiles_to_sheets[tile].add(sheet_no)
    data = { 'base_tiles_to_sheets': base_tiles_to_sheets,
             'sheets_to_base_tiles': sheets_to_base_tiles }
    return data


    
def create_tiles(inp_file, output_dir, zoom_levels):
    print('start tiling')
    os.environ['GDAL_CACHEMAX'] = '2048'
    os.environ['GDAL_MAX_DATASET_POOL_SIZE'] = '5000'
    os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'TRUE'
    #os.environ['VRT_SHARED_SOURCE'] = '1'
    #os.environ['GTIFF_VIRTUAL_MEM_IO'] = 'TRUE'
    gdal2tiles_main(['gdal2tiles.py',
                     '-r', 'antialias',
                     '--verbose',
                     '--exclude', 
                     '--resume', 
                     '--xyz', 
                     '--processes=8', 
                     '-z', zoom_levels,
                     '--tiledriver', 'WEBP',
                     '--webp-quality', '50',
                     inp_file, output_dir])


orig_tiles_dir = Path('export/tiles')
orig_tiffs_dir = Path('export/gtiffs')
tiles_dir = Path('staging/tiles')
tiffs_dir = Path('staging/gtiffs')
z_min = 2
z_max = 15

def get_tile_file(tile):
    return f'{tiles_dir}/{tile.z}/{tile.x}/{tile.y}.webp'

def get_tile_file_orig(tile):
    return f'{orig_tiles_dir}/{tile.z}/{tile.x}/{tile.y}.webp'

def copy_sheets_over(sheets_to_pull):
    for sheet_no in sheets_to_pull:
        fro = orig_tiffs_dir.joinpath(f'{sheet_no}.tif')
        to = tiffs_dir.joinpath(f'{sheet_no}.tif')
        if not fro.exists():
            continue
        shutil.copy(str(fro), str(to))

def copy_tiles_over(tiles_to_pull):
    for tile in tiles_to_pull:
        fro = Path(get_tile_file_orig(tile))
        to = Path(get_tile_file(tile))
        if not fro.exists() or to.exists():
            continue
        to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(fro), str(to))

def push_tiles(tiles_to_push):
    for tile in tiles_to_push:
        fro = Path(get_tile_file(tile))
        #to = Path(get_tile_file_orig(tile))
        to = Path(get_tile_file(tile).replace('staging', 'staging1'))
        if not fro.exists():
            continue
        to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(fro), str(to))

def create_upper_tiles(all_affected_tiles_by_zoom):
    options = AttrDict({
        'resume': True,
        'verbose': True,
        'quiet': False,
        'xyz': True,
        'exclude_transparent': True,
        'profile': 'mercator',
        'resampling': 'antialias',
        'tiledriver': 'WEBP',
        'webp_quality': 50,
    })
    tile_job_info = TileJobInfo(
        tile_driver='WEBP',
        nb_data_bands=3,
        tile_size=256,
        tile_extension='webp',
        kml=False
    )
    nb_processes = 8
    #with Pool(processes=nb_processes) as pool:
    for z in range(z_max - 1, z_min - 1, -1):
        print(f'creating overviews at level {z}')
        for tile in all_affected_tiles_by_zoom[z]:
            ctiles = mercantile.children(tile)
            tiles_dir.joinpath(str(tile.z), str(tile.x)).mkdir(parents=True, exist_ok=True)
            base_tile_group = [ (t.x, GDAL2Tiles.getYTile(t.y, t.z, options)) for t in ctiles ]
            print(f'{tile=}, {base_tile_group=}')
            create_overview_tile(z + 1, output_folder=str(tiles_dir), tile_job_info=tile_job_info, options=options, base_tiles=base_tile_group)
 




if __name__ == '__main__':
    tiles_dir.mkdir(parents=True, exist_ok=True)
    tiffs_dir.mkdir(parents=True, exist_ok=True)
    retile_sheets = Path('retile.txt').read_text().split('\n')
    retile_sheets = set([ r.strip() for r in retile_sheets if r.strip() != '' ])

    print('reading index file')
    #with open('data/index.geojson', 'r') as f:
    with open('index.geojson', 'r') as f:
        index_data = json.load(f)

    print('preparing index to tiles maps')
    sheets_to_box = {}
    for f in index_data['features']:
        sheet_no = f['properties']['EVEREST_SH'].replace('/', '_')
        box = f['geometry']['coordinates'][0][:-1]
        sheets_to_box[sheet_no] = box

    data = get_sheets_to_basetile_mapping(index_data)
    base_tiles_to_sheets = data['base_tiles_to_sheets']
    sheets_to_base_tiles = data['sheets_to_base_tiles']

    sheets_to_pull_by_sheet = {}
    all_affected_tiled_by_sheet_no = {}
    all_tiles_to_pull = set()
    full_affected_tile_list = set()
    for sheet_no in retile_sheets:
        tiles_to_pull = set()
        print(f'handling sheet - {sheet_no}')
        affected_base_tiles = set(sheets_to_base_tiles[sheet_no])

        sheets_to_pull = set()
        for btile in affected_base_tiles:
            sheets_involved = base_tiles_to_sheets[btile]
            sheets_to_pull.update(sheets_involved)

        print(f'{sheets_to_pull=}')
        sheets_to_pull_by_sheet[sheet_no] = sheets_to_pull
                        
        all_affected_tiles_by_zoom = {}
        box = sheets_to_box[sheet_no]
        all_affected_tiles = set(mercantile.tiles(box[0][0], box[2][1], box[2][0], box[0][1], range(z_min, z_max + 1))) 
        full_affected_tile_list.update(all_affected_tiles)
        print('affected tiles')
        for tile in all_affected_tiles:
            print(get_tile_file(tile))

        all_affected_tiled_by_sheet_no[sheet_no] = all_affected_tiles
        for tile in all_affected_tiles:
            if tile.z not in all_affected_tiles_by_zoom:
                all_affected_tiles_by_zoom[tile.z] = set()
            all_affected_tiles_by_zoom[tile.z].add(tile)

        for z in range(z_min, z_max):
            for tile in all_affected_tiles_by_zoom[z]:
                for ctile in mercantile.children(tile):
                    if ctile not in all_affected_tiles:
                        tiles_to_pull.add(ctile)

        print('tiles_to_pull')
        for tile in tiles_to_pull:
            print(get_tile_file(tile))
        all_tiles_to_pull.update(tiles_to_pull)

        print('pulling in sheets')
        copy_sheets_over(sheets_to_pull)
        print('pulling in tiles')
        copy_tiles_over(tiles_to_pull)
        print('deleting affected tiles')
        deleted_count = 0
        for tile in all_affected_tiles:
            tile_file = Path(get_tile_file(tile))
            if tile_file.exists():
                deleted_count += 1
                tile_file.unlink()
        print(f'deleted {deleted_count} tiles')
        # for the base level create a vrt of all the sheets needed for this sheet
        tiff_list = [ tiffs_dir.joinpath(f'{p_sheet}.tif').resolve() for p_sheet in sheets_to_pull ]
        tiff_list = [ str(f) for f in tiff_list if f.exists() ]
        tiff_list_str = ' '.join(tiff_list)
        vrt_file = Path(f'staging/{sheet_no}.vrt')
        run_external(f'gdalbuildvrt {str(vrt_file)} {tiff_list_str}')
        # and run gdal2tiles for just the base tiles
        print('creating tiles for base zoom with a vrt')
        create_tiles(str(vrt_file), str(tiles_dir), f'{z_max}')
        # then run gdal2tiles for all the other levels with just the sheet
        print('creating tiles for all levels with just the sheet')
        create_upper_tiles(all_affected_tiles_by_zoom)
        #if input(f"Done with {sheet_no}, Continue? (y/n)") != "y":
        #    exit()
    print('pushing back tiles to main')
    push_tiles(full_affected_tile_list)
    #shutil.rmtree('staging')


