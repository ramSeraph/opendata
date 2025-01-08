#!/bin/bash
set -aeux

script_dir=$(dirname "$0")
unameOut="$(uname -s)"
RUNNER="uv run"

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
  cd data > /dev/null
  wget -q https://storage.googleapis.com/lgd_data_archive/listing_archives.txt
  all_dates="$(cat listing_archives.txt| cut -d' ' -f2)"
  rm listing_archives.txt
  for d in $all_dates
  do
    d_conv=$(conv_date $d)
    if [[ $d_conv -gt $max_date_conv ]]; then
      max_date=$d
      max_date_conv=$d_conv
    fi
  done
  cd - > /dev/null
  echo ${max_date}
}


lgd_files=(
  'blocks.csv'
  'district_panchayats.csv'
  'districts.csv'
  #'gp_mapping.csv'
  'pri_local_bodies.csv'
  'states.csv'
  #'statewise_ulbs_coverage.csv'
  'subdistricts.csv'
  #'urban_local_bodies.csv'
  #'villages.csv'
  #'villages_by_blocks.csv'
)


get_lgd_files() {
  mkdir -p data/lgd
  cd data
  date_str=$(get_lgd_latest_date)
  echo "getting lgd_archive for $date_str"
  echo "$date_str" > lgd_date.txt
  # download the lgd archive
  wget https://storage.googleapis.com/lgd_data_archive/${date_str}.zip
  # unzip files
  7z x ${date_str}.zip
  # move files to lgd dir
  for file in ${lgd_files[*]}
  do
    mv "${date_str}/$file" lgd/
  done
  rm -rf ${date_str} ${date_str}.zip
  cd -
}

verify_states() {
  $RUNNER ${script_dir}/download.py state
  $RUNNER ${script_dir}/check_states.py
  
}

verify_divisions() {
  $RUNNER ${script_dir}/download.py state
  $RUNNER ${script_dir}/download.py division
  $RUNNER ${script_dir}/download.py district
  $RUNNER ${script_dir}/check_divisions.py
}

verify_districts() {
  $RUNNER ${script_dir}/download.py state
  $RUNNER ${script_dir}/download.py division
  $RUNNER ${script_dir}/download.py district
  $RUNNER ${script_dir}/check_districts.py
}

verify_subdivisions() {
  $RUNNER ${script_dir}/download.py district
  $RUNNER ${script_dir}/download.py subdivision
  $RUNNER ${script_dir}/download.py subdistrict
  $RUNNER ${script_dir}/check_subdivisions.py
}

verify_subdistricts() {
  $RUNNER ${script_dir}/download.py district
  $RUNNER ${script_dir}/download.py subdivision
  $RUNNER ${script_dir}/download.py subdistrict
  $RUNNER ${script_dir}/check_subdistricts.py
}

verify_blocks() {
  $RUNNER ${script_dir}/download.py district
  $RUNNER ${script_dir}/download.py subdivision
  $RUNNER ${script_dir}/download.py block
  $RUNNER ${script_dir}/check_blocks.py
}

verify_district_panchayats() {
  $RUNNER ${script_dir}/download.py state
  $RUNNER ${script_dir}/download.py district
  $RUNNER ${script_dir}/download.py district_panchayat
  $RUNNER ${script_dir}/check_district_panchayats.py
}

verify_block_panchayats() {
  $RUNNER ${script_dir}/download.py state
  $RUNNER ${script_dir}/download.py district_panchayat
  $RUNNER ${script_dir}/download.py block_panchayat
  $RUNNER ${script_dir}/check_block_panchayats.py
}

get_lgd_files

verify_states
verify_divisions
verify_districts
verify_subdivisions
verify_subdistricts
#verify_blocks
verify_district_panchayats
#verify_block_panchayats

$RUNNER ${script_dir}/collect_status.py



