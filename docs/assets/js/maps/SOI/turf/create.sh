#!/bin/bash
set -ex
if [[ $DELETE != "1" ]]; then
    docker run --rm -it -v "$PWD":/code -w /code/ node npm install @turf/invariant @turf/boolean-intersects @turf/bbox browserify uglify-js
    docker run --rm -it -v "$PWD":/code -w /code/ node npx browserify main.js -s turf -o turf.js 
    docker run --rm -it -v "$PWD":/code -w /code/ node npx uglifyjs turf.js -o turf.min.js 
fi

if [[ $DELETE == "1" ]]; then
    rm -rf node_modules/
    rm -rf package.json
    rm -rf package-lock.json
    rm -rf turf.js
fi

