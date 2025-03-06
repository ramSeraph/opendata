#!/bin/bash
set -aeux

script_dir=$(dirname "$0")
uname_out="$(uname -s)"
RUNNER="uv run"

conv_date() {
  if [[ $uname_out == "Darwin" ]]; then
    date -j -f "%d%b%Y" "$1" +"%s"
  else
    date -d"$1" +"%s"
  fi
}

get_lgd_latest_date() {
  prefix=$1
  max_date="01Jan1970"
  max_date_conv=$(conv_date $max_date)
  all_dates="$(cat listing_archives.txt | cut -d" " -f2 | grep "^$prefix\." | cut -d"." -f2)"
  for d in $all_dates
  do
    d_conv=$(conv_date $d)
    if [[ $d_conv -gt $max_date_conv ]]; then
      max_date=$d
      max_date_conv=$d_conv
    fi
  done
  echo ${max_date}
}


release_url="https://github.com/ramSeraph/opendata/releases/download/lgd-latest"

get_lgd_files() {
  mkdir -p data/lgd
  cd data
  wget -q ${release_url}/listing_archives.txt
  for prefix in ${lgd_file_prefixes[*]}
  do
    date_str=$(get_lgd_latest_date $prefix)
    echo "getting lgd_archive for $prefix $date_str"
    echo "$date_str" > ${prefix}.lgd_date.txt
    fname=${prefix}.${date_str}.csv.7z
    wget ${release_url}/${fname}
    7z x $fname
    rm $fname
    mv ${prefix}.${date_str}.csv lgd/${prefix}.csv
  done
  rm listing_archives.txt
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

source ${script_dir}/files.sh

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



