#!/bin/bash

if [[ $1 == 'pdfs' ]]; then
  gh release view soi-pdfs --json assets -q '.assets[] | "\(.size) \(.name)"' | grep '\.pdf' | sed 's/\.pdf//g' > list.txt
  gh release upload soi-pdfs --clobber list.txt
  rm list.txt
  exit 0
fi

if [[ $1 == 'tiffs' ]]; then
  gh release view soi-tiffs --json assets -q '.assets[] | "\(.size) \(.name)"' | grep '\.tif' | sed 's/\.tif//g' > list.txt
  gh release upload soi-tiffs --clobber list.txt
  rm list.txt
  exit 0
fi

if [[ $1 == 'jpgs' ]]; then
  gsutil ls gs://soi_data/compressed/*.jpg | cut -d"/" -f5 | cut -d"." -f1 > list.txt
  gsutil cp list.txt gs://soi_data/compressed/
  rm list.txt
fi

echo "ERROR: first argument should be one of 'pdfs', 'tiffs', 'jpgs'"
exit 1
