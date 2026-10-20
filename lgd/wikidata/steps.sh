#!/bin/bash
set -euo pipefail

cd -- "$(dirname -- "$0")"
uname_out="$(uname -s)"

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
  all_dates="$(cat listing_files.csv | cut -d"," -f1 | grep "^$prefix\." | cut -d"." -f2)"
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
  wget -q ${release_url}/listing_files.csv
  for prefix in ${lgd_file_prefixes[*]}
  do
    date_str=$(get_lgd_latest_date $prefix)
    echo "getting lgd_archive for $prefix $date_str"
    echo "$date_str" > ${prefix}.lgd_date.txt
    fname=${prefix}.${date_str}.csv.7z
    url="$(grep "^${fname}," listing_files.csv | cut -d"," -f3 | tr -d '\r')"
    wget $url
    7z x $fname
    rm $fname
    mv ${prefix}.${date_str}.csv lgd/${prefix}.csv
  done
  rm listing_files.csv
  cd -
}

source ./files.sh

get_lgd_files

datasets=(states divisions districts subdivisions subdistricts district_panchayats)

# Fetch shared inputs once before running the reports that depend on them.
for dataset in "${datasets[@]}"; do
  uv run download.py "$dataset"
done

for dataset in "${datasets[@]}"; do
  uv run "check_${dataset}.py"
done

uv run collect_status.py
