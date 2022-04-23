# -*- coding: utf-8 -*-
"""
Usage: mktiles.py <filename.tif>

Simple script to make a bunch of map tiles from a GeoTIFF file in pseudomercator 
projection.
"""

# Imports
import os
import sys
import argparse
import math
import click
import mercantile
from osgeo import gdal

# Parse the command-line arguments
parser = argparse.ArgumentParser(description='mktiles.py')
parser.add_argument('input_file', type=str, help='Input file')
args = parser.parse_args()

# Open the file and get geotransform information
ds = gdal.Open(args.input_file)
if ds is None:
    print("Could not open file!")
    sys.exit(1)
gt = ds.GetGeoTransform()
print(gt)

# Estimate a maximum and minimum z level to fit the image, and show some 
# prompts with defaults that the use can override
#z_max_default = int(math.floor(math.log(40075016.0, gt[1]) - 8) - 1)
z_max_default = 15
z_max = click.prompt("Maximum Z level", default=z_max_default, type=int)

z_min_default = int(z_max - math.ceil(math.log(max(ds.RasterXSize, 
                                                   ds.RasterYSize) / 256, 2)))
print(z_min_default)
z_min_default = 2
z_min = click.prompt("Minimum Z level", default=z_min_default, type=int)

# Get the geographic coordinates of the file's left top and right bottom 
lt = mercantile.lnglat(gt[0], gt[3])
rb = mercantile.lnglat(gt[0] + (ds.RasterXSize * gt[1]), 
                       gt[3] + (ds.RasterYSize * gt[5]))

# Use the coordinates and z levels we create a list of tiles to generate
tiles = list(mercantile.tiles(lt.lng, rb.lat, rb.lng, lt.lat, 
                              range(z_min, z_max + 1)))
num_tiles = len(tiles)

# Ask for confirmation before proceeding
if not click.confirm("Going to create {} tiles. Continue?".format(num_tiles),
                     default=True):
  sys.exit(1)

# Loop through all the the tiles, and render each one using gdal.Translate()
with click.progressbar(tiles) as bar:
  for tile in bar:      
      # Create the filename and directory for the tile
      filename = "./tiles/{}/{}/{}.jpg".format(tile.z, tile.x, tile.y)
      #print("Creating tile {}".format(filename))
      try: os.makedirs(os.path.dirname(filename))
      except: pass

      # Convert tile bounds to a projwin for passing to gdal.Translate()
      (left, bottom, right, top) = list(mercantile.xy_bounds(tile))
      projwin = (left, top, right, bottom)

      # Call gdal.Translate()
      gdal.Translate(filename, 
                     ds, 
                     projWin=projwin, 
                     width=256, 
                     height=256, 
                     format='JPEG', 
                     creationOptions=['QUALITY=75'])

      # Remove the automatically create xml file 
      os.remove(filename+'.aux.xml')
