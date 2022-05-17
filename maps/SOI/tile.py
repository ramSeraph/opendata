#GDAL_LIBRARY_PATH = "/opt/homebrew/lib/libgdal.dylib"
#import ctypes
#ctypes.CDLL(GDAL_LIBRARY_PATH)
import os
import glob
import json
#os.environ['SPATIALINDEX_C_LIBRARY'] = '/opt/homebrew/lib/'

import math
import time
import os.path
import subprocess

from pathlib import Path
from multiprocessing import freeze_support
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image, UnidentifiedImageError
import mercantile
from osgeo import gdal
#from rtree import index
#from osgeo_utils.gdal2tiles import main as gdal2tiles_main

from gdal2tiles import main as gdal2tiles_main

from tile_helper import (setup_lists, add_to_excluded,
                         add_to_ondisk_tiles, get_done_dir_list)

OVERWRITE=False

index_map = {}
USE_INDEX_FILE = True
if USE_INDEX_FILE:
    print('reading index file')
    with open('data/index.geojson') as fp:
        index_data = json.load(fp)
        for f in index_data['features']:
            sheet_no = f['properties']['EVEREST_SH'].replace('/', '_')
            index_map[sheet_no] = f


vrt_ds = None

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

def file_to_tiles_using_index(file_name):
    global index_map
    z_min = 2
    z_max = 15
    sheet_no = Path(file_name).name.replace('.tif', '')
    f = index_map[sheet_no]
    box = f['geometry']['coordinates'][0][:-1]
    tiles = set(mercantile.tiles(box[0][0], box[2][1], box[2][0], box[0][1], 
                                  range(z_min, z_max + 1)))
    return tiles



def file_to_tiles(file_name):
    if USE_INDEX_FILE:
        return file_to_tiles_using_index(file_name)
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

def is_tile_transperent(filename):
    img = Image.open(filename)
    alpha = img.split()[-1]
    a = np.array(alpha)
    total = a.shape[0] * a.shape[1]
    nodata = np.count_nonzero(a == 0)
    if nodata == total:
        return True
    return False

def get_vol_inode():
    res = subprocess.run('stat "/Volumes/One Touch"', shell=True, capture_output=True, text=True)
    vol_inode = int(res.stdout.split(' ')[0])
    return vol_inode

def populate_ondisk_details(tiles_dir, tileext):
    vol_inode = get_vol_inode()
    setup_lists()
    tileext = '.' + tileext
    print('collecting ondisk file details')
    start = time.time()
    all_tiles = set()
    tile_dirs = set()
    z_folders = [
        (int(de.name), de.inode())
        for de in os.scandir(tiles_dir)
        if de.is_dir(follow_symlinks=False) and de.name.isdigit()
    ]
    done_folders = get_done_dir_list()
    done_folders = set(done_folders[:-1])

    done = 0
    excluded = 0
    for z, z_inode in z_folders:
        print(f'scanning {z=}')
        alt_file = f'/.vol/{vol_inode}/{z_inode}'
        des = os.scandir(alt_file)
        for de in des:
            if not de.name.isdigit() or not de.is_dir(follow_symlinks=False):
                continue
            x = int(de.name)
            x_inode = de.inode()
            print(f'scanning {z=} {x=}')
            if (z,x) in done_folders:
                print(f'skipping done folder')
                continue
            alt_file_x = f'/.vol/{vol_inode}/{x_inode}'
            deys = os.scandir(alt_file_x)
            for dey in deys:
                if not dey.is_file(follow_symlinks=False) or not dey.name.endswith(tileext):
                    continue
                y = int(dey.name.replace(tileext, ''))
                y_inode = dey.inode()
                alt_file_y = f'/.vol/{vol_inode}/{y_inode}'
                try:
                    exclude = is_tile_transperent(alt_file_y)
                except UnidentifiedImageError as ex:
                    print(f'got unidentified image error while dealing with {z=}, {x=}, {y=}, deleting file')
                    os.remove(alt_file_y)
                    done += 1
                    continue
                if is_tile_transperent(alt_file_y):
                    add_to_excluded(z, x, y)
                    os.remove(alt_file_y)
                    excluded += 1
                else:
                    add_to_ondisk_tiles(z, x, y, y_inode)
                done += 1

                if (done % 1000) == 0:
                    print(f'{done=}, {excluded=}')





if __name__ == '__main__':
    import sys
    freeze_support()
    tiles_dir = Path('export/tiles')

    tiles_dir.mkdir(parents=True, exist_ok=True)
    file_list_file = Path('export/files_to_tile.txt')
    file_names = list(glob.glob('export/gtiffs/*.tif'))
    file_names = [ str(Path(f).resolve()) for f in file_names ]
    print(f' total files: {len(file_names)}')
    file_list_file.write_text('\n'.join(file_names))
    vrt_file = Path('export/files_to_tile.vrt')
    prev_list_file = Path('export/prev_files_to_tile.json')
    if prev_list_file.exists():
        with open(prev_list_file) as f:
            prev_info = json.load(f)
    else:
        prev_info = {}

    cur_set = set(file_names) 
    prev_set = set(prev_info.keys())
    to_add = cur_set - prev_set
    to_remove = prev_set - cur_set
    if len(to_remove) > 0:
        raise Exception('currently removing for tiling list is not supported.. redo?')



    cur_info = get_file_info(file_names)
    files_to_do = get_updated_files(cur_info, prev_info)
    print(f'files to do: {len(files_to_do)}')
    if len(files_to_do) == 0:
        exit(0)
    tiles_to_update = get_affected_tile_set(files_to_do)
    print(f'{len(tiles_to_update)=}')
    existing_tiles = get_affected_tile_set(set(prev_info.keys()))
    new_tiles = tiles_to_update - existing_tiles
    to_delete_tiles = tiles_to_update - new_tiles
    print(f'{len(to_delete_tiles)=}')

    print(f'deleting overlapping files')
    delete_count = 0
    for tile in to_delete_tiles:
        tile_file = tiles_dir.joinpath(f'{tile.z}/{tile.x}/{tile.y}.webp')
        delete_count += 1
        if (delete_count % 100) == 0:
            print(f'done deleting {delete_count}')

        if tile_file.exists():
            #print(f'deleting file {tile_file}')
            tile_file.unlink()
            #update_ondisk_details(tile.z, tile.x, tile.y, 'del')

    # create vrt file
    run_external(f'gdalbuildvrt -input_file_list {str(file_list_file)} {str(vrt_file)}')
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
                     '-z', '2-15',
                     '--tiledriver', 'WEBP',
                     '--webp-quality', '50',
                     str(vrt_file), str(tiles_dir)])

    with open(prev_list_file, 'w') as f:
        json.dump(cur_info, f, indent=2)
    print('All Done!!')
