#!/bin/bash

gh release download soi-tiffs -p listing_files.csv -O tiffs_listing.csv --clobber
gh release download soi-latest -p listing_files.csv -O tiled_listing.csv --clobber

comm -23 <(cat tiffs_listing.csv| cut -d"," -f1 | cut -d"." -f1 | sort) <(cat tiled_listing.csv | cut -d"," -f1 | cut -d"." -f1 | sort) | cut -f1 | sed '/^[[:space:]]*$/d' > $1

rm tiled_listing.csv tiffs_listing.csv
