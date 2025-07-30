#!/bin/bash

gh release download soi-pdfs -p listing_files.csv -O pdfs_listing.csv --clobber
gh release download soi-tiffs -p listing_files.csv -O tiffs_listing.csv --clobber

comm -23 <(cat pdfs_listing.csv| cut -d"," -f1 | cut -d"." -f1 | sort) <(cat tiffs_listing.csv | cut -d"," -f1 | cut -d"." -f1 | sort) | cut -f1 | sed '/^[[:space:]]*$/d' > temp.txt

uv run python -c "from known_problems import known_problems as kp; l = [ k.replace('data/raw/', '').replace('.pdf', '') for k in  kp ]; print('\n'.join(l))" > kp.txt

comm -23 <(cat temp.txt | sort) <(cat kp.txt | sort) | cut -f1 | sed '/^[[:space:]]*$/d' > $1

rm pdfs_listing.csv tiffs_listing.csv temp.txt kp.txt
