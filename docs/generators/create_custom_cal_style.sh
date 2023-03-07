#!/bin/bash
# used to create flatpickr.min.js and flatpickr_dark_custom.min.css, not meant to be served directly

set -ex

SETUP=${SETUP:-"0"}
CLEANUP=${CLEANUP:-"0"}
BUILD=${BUILD:="1"}
version="4.6.13"
if [[ $SETUP == 1 ]]; then
    echo "blah"
    #wget https://github.com/flatpickr/flatpickr/archive/refs/tags/v${version}.zip 
    #unzip v${version}.zip
    #rm v${version}.zip
fi

cd flatpickr-${version}

if [[ $SETUP == 1 ]]; then
    docker run --rm -it -v "$PWD":/code -w /code/ node npm install
fi

if [[ $BUILD == 1 ]]; then
    #patch -s -p0 < ../flaptpickr.patch
    docker run --rm -it -v "$PWD":/code -w /code/ node npm run build
    cp dist/flatpickr.min.js ../../assets/js/lgd/
    cp dist/themes/flatpickr_dark_custom.min.css ../../assets/css/lgd/
fi

cd ..

if [[ $CLEANUP == 1 ]]; then
    rm -rf flatpickr-${version}
fi
