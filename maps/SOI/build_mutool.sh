#!/bin/bash

[[ -e bin/mutool ]] && exit 0
git clone https://github.com/ArtifexSoftware/mupdf
cd mupdf
git checkout 1.20.0-rc1
git submodule update --init
git apply ../mupdf.patch
make HAVE_X11=no HAVE_GLUT=no
mkdir -p ../bin
cp build/release/mutool ../bin/ 
cd ..
rm -rf mupdf/
