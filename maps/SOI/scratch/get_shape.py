from shapely.geometry import box
from shapely.ops import unary_union
import mercantile
import glob
from pprint import pprint


files = glob.glob('14/*/*.webp')
tiles = []
for file in files:
    parts = file.split('/')
    tile = mercantile.Tile(z=int(parts[0]),
                           x=int(parts[1]),
                           y=int(parts[2].replace('.webp', '')))
    tiles.append(tile)

bounds = [ mercantile.bounds(t) for t in tiles ]

max_x = bounds[0].east
min_x = bounds[0].west
max_y = bounds[0].north
min_y = bounds[0].south
for b in bounds:
    if b.east > max_x:
        max_x = b.east

    if b.west < min_x:
        min_x = b.west

    if b.north > max_y:
        max_y = b.north

    if b.south < min_y:
        min_y = b.south

print(f'{min_y=}, {max_y=}, {min_x=}, {max_x=}')
center = ((min_y + max_y)/2.0, (min_x + max_x)/2.0, 8)
print(f'{center=}')

boxes  = [ box(b.west, b.east, b.south, b.north) for b in bounds ]
full_shape = unary_union(boxes)

print(f'{full_shape.centroid=}')
print(f'{full_shape.bounds=}')
