#!/bin/bash

set -e

mkdir -p data

echo "pull existing sitemap"
gh release download lgd-latest -p site_map.json -O data/site_map_old.json

cat scrape/site_map.json | jq --indent 0 . > data/site_map.json

set +e
cmp --silent data/site_map_old.json data/site_map.json
ret=$?
set -e

if [[ $ret != 0 ]]; then
    echo 'uploading changed sitemap'
    gh release upload lgd-latest data/site_map.json --clobber
fi

echo "cleaning up"
rm data/site_map.json data/site_map_old.json
