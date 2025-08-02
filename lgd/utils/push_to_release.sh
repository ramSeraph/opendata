#!/bin/bash

set -ex

echo "Fetching list of existing .7z files from GitHub releases..."
RELEASE_FILES_LIST="existing_release_files.txt"
gh release list --jq '.[] | select(.name | startswith("lgd-latest")) | .name' | while read -r release_name; do
  gh release view "$release_name" --json assets --jq '.assets[]? | select(.name | endswith(".7z")) | .name' 2>/dev/null
done > "$RELEASE_FILES_LIST"
echo "Found $(wc -l < "$RELEASE_FILES_LIST") existing .7z files."

curr_date=$1
to_del_7zs=()
while read comp; do
  echo "handling $comp"
  if [[ $comp == "CHANGES" ]]; then

    cd data/raw/$curr_date
    7z a changes.csv.7z changes.csv
    gh release upload lgd-latest changes.csv.7z --clobber
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
    if grep -qFx "$new_fname_7z" "$RELEASE_FILES_LIST"; then
      echo "Skipping $new_fname_7z as it already exists in a release."
    else
      cd data/raw/$curr_date
      cp $fname $new_fname
      7z a ${new_fname}.7z ${new_fname}
      rm $new_fname
      to_del_7zs+=("${new_fname}.7z")
      cd -
    fi
  fi
done < done_comps.txt

uvx --from topo_map_processor upload-to-release lgd-latest data/raw/$curr_date '7z'

for f in "${to_del_7zs[@]}"; do
  echo "deleting $f"
  rm data/raw/$curr_date/$f
done

rm "$RELEASE_FILES_LIST"
