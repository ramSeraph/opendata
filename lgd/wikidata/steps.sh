#!/bin/bash
set -aux


date=16Apr2024
lgd_files=(
  'blocks.csv'
  'districts.csv'
  'gp_mapping.csv'
  'pri_local_bodies.csv'
  'states.csv'
  'subdistricts.csv'
  'urban_local_bodies.csv'
  'villages.csv'
  'villages_by_blocks.csv'
)

mkdir -p data/lgd

get_lgd_files() {

  cd data
  # download the lgd archive
  wget https://storage.googleapis.com/lgd_data_archive/${date}.zip
  # unzip files
  7z x ${date}.zip
  # move files to lgd dir
  for file in ${lgd_files[*]}
  do
    mv "${date}/$file" lgd/
  done
  rm -rf ${date}
  cd -
}

verify_states() {
    python download.py state
    python check_states.py
  
}

verify_divisions() {
    python download.py state
    python download.py division
    python check_districts.py
}

verify_districts() {
    python download.py state
    python download.py division
    python download.py district
    python check_districts.py
}

verify_subdivisions() {
    python download.py district
    python download.py subdivision
    python check_subdivisions.py
}

verify_subdistricts() {
    python download.py district
    python download.py subdivision
    python download.py subdistrict
    python check_subdistricts.py
}

#get_lgd_files

verify_states
verify_divisions
verify_districts
verify_subdivisions
verify_subdistricts



