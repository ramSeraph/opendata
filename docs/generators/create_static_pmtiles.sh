#!/bin/bash

wget https://storage.googleapis.com/soi_data/index.geojson
ogr2ogr -f FlatGeobuf index.fgb index.geojson
tippecanoe -zg -o index.pmtiles --drop-densest-as-needed index.fgb
gsutil -h "Cache-Control:public, max-age=31535000" cp index.pmtiles gs://soi_data/
rm index.fgb
rm index.geojson
rm index.pmtiles
exit


wget https://www.surveyofindia.gov.in/documents/India%20Outline%20Map.zip
unzip "India Outline Map.zip" -d "India Outline Map"
ogr2ogr -f FlatGeobuf -s_srs "India Outline Map/polymap15m_area.prj" -t_srs EPSG:4326 polymap15m_area.fgb "India Outline Map/polymap15m_area.shp"
tippecanoe -zg -o polymap15m_area.pmtiles --drop-densest-as-needed polymap15m_area.fgb
gsutil -h "Cache-Control:public, max-age=31535000" cp polymap15m_area.pmtiles gs://soi_data/
rm polymap15m_area.fgb
rm polymap15m_area.pmtiles
rm -rf "India Outline Map.zip"
rm -rf "India Outline Map/"

wget https://raw.githubusercontent.com/datameet/maps/master/website/docs/data/geojson/states.geojson
ogr2ogr -f FlatGeobuf states.fgb states.geojson
tippecanoe -zg -o states.pmtiles --drop-densest-as-needed states.fgb
gsutil -h "Cache-Control:public, max-age=31535000" cp states.pmtiles gs://soi_data/
rm states.geojson
rm states.fgb
rm states.pmtiles
