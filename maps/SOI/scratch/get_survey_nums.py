GDAL_LIBRARY_PATH = "/opt/homebrew/lib/libgdal.dylib"
import ctypes
ctypes.CDLL(GDAL_LIBRARY_PATH)
import os
os.environ['SPATIALINDEX_C_LIBRARY'] = '/opt/homebrew/lib/'


import json
from rtree import index
from shapely.geometry import shape
from shapely.prepared import prep

prepared_map = {}

def idx_gen():
    i = 0
    geojson_files = ['index.geojson']
    #geojson_files = glob.glob('composite/*/districts.geojson')
    for geojson_file in geojson_files:
        print('processing {} for building OSM_SHEET_INDEX index'.format(geojson_file))
        with open(geojson_file) as f:
            data = json.load(f)

        for feature in data['features']:
            s = shape(feature['geometry'])
            if not s.is_valid:
                print('invalid geometry for {}, fixing with buffer(0)'.format(feature['properties']))
                s = s.buffer(0)
                if not s.is_valid:
                    print('invalid geometry even after buffer for {}'.format(feature['properties']))
            g = prep(s)
            feature['geometry'] = s
            prepared_map[i] = g
            feature['id'] = i
            #print('sending {}, {}, {}'.format(i, s.bounds, feature['properties']))
            yield (i, s.bounds, feature)
            i += 1


print('building subdistrict index')
idx = index.Index(idx_gen())

#dist_name = 'REWA'
#with open('/Users/ram/Code/old_opendata/data/maps/osm/composite/districts.geojson') as f:
#    dist_data = json.load(f)

#dist_shape = None
#for feature in dist_data['features']:
#    if feature['properties']['name'] == dist_name:
#        dist_shape = shape(feature['geometry'])
#        break

lat = 30.267554
lng = 80.0013256
dist_bounds = (lng, lat, lng, lat)
idx_features = [n.object for n in idx.intersection(dist_bounds, objects=True)]

infos = []
for idx_feature in idx_features:
    #pg = prepared_map[idx_feature['id']]
    #if pg.intersects(dist_shape):
    infos.append(idx_feature['properties'])

for info in infos:
    print(f'{info}')


