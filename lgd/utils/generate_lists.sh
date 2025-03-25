#!/bin/bash

release=$1

echo "getting file list"
gh release view $release --json assets -q '.assets[] | "\(.size) \(.name)"' | grep '.7z$' > listing_archives.txt
cat listing_archives.txt | cut -d" " -f2 | xargs -I {} echo "https://github.com/ramSeraph/opendata/releases/download/$release/{}" > url_list.txt

echo "uploading listing"
gh release upload $release listing_archives.txt --clobber
gh release upload $release url_list.txt --clobber

rm listing_archives.txt url_list.txt
