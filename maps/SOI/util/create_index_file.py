import os
import json
import shutil
from pathlib import Path

def correct_index_file(out_filename):
    with open(out_filename, 'r') as f:
        index_data = json.load(f)

    corrections_file = Path(__file__).parent.joinpath('index.geojson.corrections')
    with open(corrections_file, 'r') as f:
        index_corrections_data = json.load(f)

    corrections_map = {f['properties']['EVEREST_SH']:f for f in index_corrections_data['features']}

    for f in index_data['features']:
        sheet_no = f['properties']['EVEREST_SH']
        if sheet_no not in corrections_map:
            continue
        geom_correction = corrections_map[sheet_no]['geometry']
        f['geometry'] = geom_correction

    out_filename_new = out_filename + '.new'
    with open(out_filename_new, 'w') as f:
        json.dump(index_data, f, indent=4)
    shutil.move(out_filename_new, out_filename)


shp_file = 'data/raw/OSM_SHEET_INDEX/OSM_SHEET_INDEX.shp'
out_filename = 'data/index.geojson'
os.system(f'ogr2ogr -f GeoJSON -t_srs EPSG:4326 {out_filename} {shp_file}')
correct_index_file(out_filename)
