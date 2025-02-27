#!/bin/bash

if [[ $1 == 'pdfs' ]]; then
  gh release view soi-pdfs --json assets -q '.assets[] | "\(.size) \(.name)"' > list.txt
  gh release upload soi-pdfs list.txt
  exit 0
fi

if [[ $1 == 'tiffs' ]]; then
  gh release view soi-tiffs --json assets -q '.assets[] | "\(.size) \(.name)"' > list.txt
  gh release upload soi-tiffs list.txt
  exit 0
fi

echo "ERROR: first argument should be one of 'pdfs' or 'tiffs'"
exit 1
