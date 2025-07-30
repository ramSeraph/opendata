#!/bin/bash

work_file=$1

gh release download soi-pdfs -p listing_files.csv --clobber

cat $work_file | xargs -I {} bash -c "[[ -e data/raw/{}.pdf ]] || echo {}.pdf" > to_download.txt
for file in $(cat to_download.txt); do
    echo "Downloading $file"
    cat listing_files.csv | grep "^${file},$" | cut -d"," -f3 | xargs -I {} wget -P data/raw {}
done
rm to_download.txt listing_files.csv
