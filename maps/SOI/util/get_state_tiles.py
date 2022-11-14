import sys
import mercantile
import json
import shapely
from shapely.geometry import shape, box

state_name = sys.argv[1]
state_geom = None
with open('states.geojson', 'r') as f:
    data = json.load(f)
for f in data['features']:
    if f['properties']['ST_NM'].lower() == state_name.lower():
        state_geom = f['geometry']

state_shape = shape(state_geom)
bbox = state_shape.bounds
(lon_min, lat_min, lon_max, lat_max) = bbox

tiles = mercantile.tiles(lon_min, lat_min, lon_max, lat_max, [15]) 
for t in tiles:
    bounds = mercantile.bounds(t)
    tile_box = box(bounds.west, bounds.south, bounds.east, bounds.north)
    if not tile_box.intersects(state_shape):
        continue
    tile_url = f'https://storage.googleapis.com/soi_data/export/tiles/{t.z}/{t.x}/{t.y}.webp'
    print(tile_url)
