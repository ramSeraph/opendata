#!/bin/bash
set -aux

script_dir=$(dirname "$0")
unameOut="$(uname -s)"

conv_date() {
  if [[ $unameOut == "Darwin" ]]; then
    date -j -f "%d%b%Y" "$1" +"%s"
  else
    date -d"$1" +"%s"
  fi
}

get_lgd_latest_date() {
  max_date="01Jan1970"
  max_date_conv=$(conv_date $max_date)
  cd data
  wget -q https://storage.googleapis.com/lgd_data_archive/listing_archives.txt
  all_dates="$(cat listing_archives.txt| cut -d' ' -f2)"
  for d in $all_dates
  do
    d_conv=$(conv_date $d)
    echo "date: $d_conv"
    if [[ $d_conv -gt $max_date_conv ]]; then
      max_date=$d
      max_date_conv=$d_conv
    fi
  done
  cd -
  echo ${max_date}
}

date=$(get_lgd_latest_date)

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
    python ${script_dir}/download.py state
    python ${script_dir}/check_states.py
  
}

verify_divisions() {
    python ${script_dir}/download.py state
    python ${script_dir}/download.py division
    python ${script_dir}/check_districts.py
}

verify_districts() {
    python ${script_dir}/download.py state
    python ${script_dir}/download.py division
    python ${script_dir}/download.py district
    python ${script_dir}/check_districts.py
}

verify_subdivisions() {
    python ${script_dir}/download.py district
    python ${script_dir}/download.py subdivision
    python ${script_dir}/check_subdivisions.py
}

verify_subdistricts() {
    python ${script_dir}/download.py district
    python ${script_dir}/download.py subdivision
    python ${script_dir}/download.py subdistrict
    python ${script_dir}/check_subdistricts.py
}

get_lgd_files

verify_states
verify_divisions
verify_districts
verify_subdivisions
verify_subdistricts



