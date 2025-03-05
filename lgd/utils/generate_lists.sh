#!/bin/bash

echo "getting file list"
gh release view lgd-latest --json assets -q '.assets[] | "\(.size) \(.name)"' | grep '.7z$' > listing_archives.txt
echo "uploading listing"
gh release upload lgd-latest listing_archives.txt --clobber
