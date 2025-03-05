#!/bin/bash
find data/raw/villages -type f | grep 'data.zip' | sed "s/.data.zip$//" | xargs -I {} sh -c "cd '{}'; unzip data.zip"
find data/raw/villages -type f | grep '.shp$' | sed 's/.shp$//' | xargs -I {} ogr2ogr -t_srs EPSG:4326 -f GeoJSONSeq '{}.geojsonl' -s_srs '{}.prj' '{}.shp'
