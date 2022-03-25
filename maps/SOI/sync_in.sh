#!/bin/bash

cd data
gsutil -m cp gs://soi_private/users_extra.json users_extra.json
gsutil -m cp gs://soi_private/users.json users.json

#gsutil -m cp gs://soi_data/index.geojson idex.geojson
gsutil -m rsync -r gs://soi_data/raw/ raw/
