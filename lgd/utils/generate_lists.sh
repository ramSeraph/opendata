#!/bin/bash

echo "getting file list"
gh release view lgd-latest --json assets -q '.assets[] | "\(.size) \(.name)"' | grep '.7z$' > listing_archives.txt
cat listing_archives.txt | cut -d" " -f2 | xargs -I {} echo "https://github.com/ramSeraph/opendata/releases/download/lgd-latest/{}" > url_list.txt

echo "uploading listing"
gh release upload lgd-latest listing_archives.txt --clobber
gh release upload lgd-latest url_list.txt --clobber

rm listing_archives.txt url_list.txt
