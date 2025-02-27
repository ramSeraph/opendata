#!/bin/bash

if [[ $1 == 'pdfs' ]]; then
  gh release view soi-pdfs --json assets -q '.assets[] | "\(.size) \(.name)"' | grep '\.pdf' > list.txt
  gh release upload soi-pdfs --clobber list.txt
  rm list.txt
  exit 0
fi

if [[ $1 == 'tiffs' ]]; then
  gh release view soi-tiffs --json assets -q '.assets[] | "\(.size) \(.name)"' | grep '\.tiff' > list.txt
  gh release upload soi-tiffs --clobber list.txt
  rm list.txt
  exit 0
fi

echo "ERROR: first argument should be one of 'pdfs' or 'tiffs'"
exit 1
