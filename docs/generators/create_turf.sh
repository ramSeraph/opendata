#!/bin/bash
# used to create turf.min.js, not meant to be served directly
set -ex
docker run --rm -it -v "$PWD":/code -w /code/ node npm install @turf/invariant @turf/boolean-intersects @turf/bbox browserify uglify-js
docker run --rm -it -v "$PWD":/code -w /code/ node npx browserify turf_main.js -s turf -o turf.js 
docker run --rm -it -v "$PWD":/code -w /code/ node npx uglifyjs turf.js -o turf.min.js 
rm -rf node_modules/
rm -rf package.json
rm -rf package-lock.json
rm -rf turf.js
mv turf.min.js ../assets/js/maps/SOI/
