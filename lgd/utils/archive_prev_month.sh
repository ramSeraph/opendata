#!/bin/bash

month_year=$1

gh release view lgd-latest --json assets -q '.assets[] | "\(.name)"' | grep "${month_year}.csv" > to_archive.txt

mkdir -p data/zipping_area
while read aname; do
    7z l -ba $file | tr -s " " | rev | cut -d" " -f1 | rev
done
