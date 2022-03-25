#!/bin/bash

cd data
gsutil -m cp users_extra.json gs://soi_private/users_extra.json

gsutil -m cp index.geojson gs://soi_data/index.geojson

gsutil -m rsync -r raw gs://soi_data/raw/
gsutil -m acl ch -r -u AllUsers:R gs://soi_data/raw/
