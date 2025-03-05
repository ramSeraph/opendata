#!/bin/bash

set -ex

curr_date=$1
set +e
gh release view lgd-latest --json assets -q '.assets[] | "\(.name)"' | grep '.7z$' | grep $curr_date > already_pushed.txt
set -e
while read comp; do
  echo "handling $comp"
  if [[ $comp == "CHANGES" ]]; then
    cd data/raw/$curr_date
    7z a changes.csv.7z changes.csv
    gh release upload lgd-latest changes.csv.7z
    rm changes.csv.7z
    cd -
    cp data/raw/changes/dates_covered.txt data/raw/changes/changes_dates_covered.txt
    gh release upload lgd-latest data/raw/changes/changes_dates_covered.txt
    rm data/raw/changes/changes_dates_covered.txt
  else
    fname=$(cat scrape/site_map.json | jq -r --arg comp $comp '.[] | select(.comp == $comp) | .file')
    prefix=${fname%.csv}
    new_fname=${prefix}.${curr_date}.csv
    new_fname_7z=${new_fname}.7z
    set +e
    grep -q $new_fname_7z already_pushed.txt
    ret=$?
    set -e
    if [[ $ret == 0 ]]; then
      continue
    fi
    cd data/raw/$curr_date
    cp $fname $new_fname
    7z a ${new_fname}.7z ${new_fname}
    gh release upload lgd-latest ${new_fname}.7z
    rm ${new_fname_7z} ${new_fname}
    cd -
  fi
done < done_comps.txt
rm already_pushed.txt
