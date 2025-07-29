#!/bin/bash

set -ex

curr_date=$1
to_del=()
to_del_7zs=()
while read comp; do
  echo "handling $comp"
  if [[ $comp == "CHANGES" ]]; then
    cd data/raw/$curr_date
    7z a changes.csv.7z changes.csv
    gh release upload lgd-latest changes.csv.7z --clobber
    to_del+=("changes.csv")
    to_del_7zs+=("changes.csv.7z")
    cd -
    cp data/raw/changes/dates_covered.txt data/raw/changes/changes_dates_covered.txt
    gh release upload lgd-latest data/raw/changes/changes_dates_covered.txt --clobber
    rm data/raw/changes/changes_dates_covered.txt
  else
    fname=$(cat scrape/site_map.json | jq -r --arg comp $comp '.[] | select(.comp == $comp) | .file')
    prefix=${fname%.csv}
    new_fname=${prefix}.${curr_date}.csv
    new_fname_7z=${new_fname}.7z
    cd data/raw/$curr_date
    cp $fname $new_fname
    7z a ${new_fname}.7z ${new_fname}
    to_del+=("$fname")
    to_del_7zs+=("${new_fname}.7z")
    cd -
  fi
done < done_comps.txt

uvx --from topo_map_processor upload-to-release lgd-latest data/raw/$curr_date '7z'

for f in "${to_del[@]}"; do
  echo "deleting $f"
  rm data/raw/$curr_date/$f
done

for f in "${to_del_7zs[@]}"; do
  echo "deleting $f"
  rm data/raw/$curr_date/$f
done
