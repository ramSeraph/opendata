import sys
import mercantile
from rasterio.crs import CRS
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps, rowcol

# script which was used to locate the XYZ tile at zoom level 15 containing a coordinate

def coords_to_tile_pos(lon, lat):
    tile = mercantile.tile(lon, lat, 15)
    
    (left, bottom, right, top) = mercantile.xy_bounds(tile)
    print(left, bottom, right, top)
    gcp1 = GroundControlPoint(row=0, col=0, x=left, y=top)
    gcp2 = GroundControlPoint(row=255, col=0, x=left, y=bottom)
    gcp3 = GroundControlPoint(row=255, col=255, x=right, y=bottom)
    gcp4 = GroundControlPoint(row=0, col=255, x=right, y=top)
    transformer = from_gcps([gcp1, gcp2, gcp3, gcp4])
    
    x, y = mercantile._xy(lon, lat)
    rs, cs = rowcol(transformer, [x], [y])
    return tile, rs[0], cs[0]

def tile_pos_to_coords(tile, row, col):
    pass

if __name__ == '__main__':
    import json
    with open('KarnatakaStations.json', 'r') as f:
        data = json.load(f)
    out = []
    for s in data:
        print(s)
        tile, row, col = coords_to_tile_pos(s['longitude'], s['latitude'])
        details = {
            "ps_id": s['ps_id'],
            "z": tile.z,
            "y": tile.y,
            "x": tile.x,
            "row": row,
            "col": col
        }
        print(details)
        exit(0)
        out.append(details)
    print(out)

    # 'latitude': 16.05661, 'longitude': 75.94569
    # row: 222, col: 188, 'z': 15, 'y': 14902, 'x': 23296



