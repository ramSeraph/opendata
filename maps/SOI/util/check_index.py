import json
from shapely.geometry import Polygon
from pathlib import Path
from functools import cmp_to_key

filename = 'data/index.geojson'

with open(filename) as f:
    data = json.load(f)

corrections_file = Path(__file__).parent.joinpath('index.geojson.corrections')
with open(corrections_file, 'r') as f:
    index_corrections_data = json.load(f)

corrections_map = {f['properties']['EVEREST_SH']:f for f in index_corrections_data['features']}

features = data['features']
for f in features:
    sheet_no = f['properties']['EVEREST_SH']
    if sheet_no in corrections_map:
        geom_correction = corrections_map[sheet_no]['geometry']
        f['geometry'] = geom_correction
    geom = f['geometry']
    poly = geom['coordinates']
    if len(poly) != 1:
        raise Exception(f'{sheet_no}: length of polygon array is not 1')
    coords = poly[0]
    if len(coords) != 5:
        print(f'length of coords is {len(coords)}')
        print(f'{f}')

    if coords[4] != coords[0]:
        print(f'coords not closed properly for {sheet_no}')
    box = Polygon(coords)
    if box.exterior.is_ccw:
        print(f'{sheet_num} is ccw')

    for c in coords:
        cx = round(c[0], 2)
        cy = round(c[1], 2)
        sx = cx * 4
        sy = cy * 4
        dx = abs(sx - round(sx))
        dy = abs(sy - round(sy))
        if dx > 0 or dy > 0:
            print(f'bad coords - {cx}, {cy} for {sheet_no}')

#for f in features:
#    sheet_no = f['properties']['EVEREST_SH']
#    adjust_coordinates(f)

    


    

