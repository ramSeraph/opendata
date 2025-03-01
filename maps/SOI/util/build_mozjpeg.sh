#!/bin/bash

# for installing on mac m1 follow instruction in below link
# https://stackoverflow.com/questions/78456062/error-while-installing-imagemin-mozjpeg-on-macos-npm-err-spawn-unknown-syste
#

npm i mozjpeg
mkdir -p bin
cp node_modules/mozjpeg/vendor/cjpeg bin/
rm -rf node_modules
