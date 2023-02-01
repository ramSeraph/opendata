wget https://www.surveyofindia.gov.in/documents/India%20Outline%20Map.zip
unzip "India Outline Map.zip" - d "India Outline Map"
ogr2ogr -f FlatGeobuf -s_srs "India Outline Map/polymap15m_area.prj" -t_srs EPSG:4326 polymap15m_area.fgb "India Outline Map/polymap15m_area.shp"
gzip polymap15m_area.fgb
rm -rf "India Outline Map.zip"
rm -rf "India Outline Map/"
gsutil -h "Cache-Control:public, max-age=31535000" cp polymap15m_area.fgb gs://soi_data/
rm polymap15m_area.fgb

wget https://raw.githubusercontent.com/datameet/maps/master/website/docs/data/geojson/states.geojson
ogr2ogr -f FlatGeobuf states.fgb states.geojson
gsutil -h "Cache-Control:public, max-age=31535000" cp states.fgb gs://soi_data/
rm states.fgb
