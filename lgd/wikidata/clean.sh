#!/bin/bash

set -aeu

script_dir=$(dirname "$0")

source ${script_dir}/files.sh

data_files=(
  'states.jsonl'
  'divisions.jsonl'
  'districts.jsonl'
  'subdivisions.jsonl'
  'subdistricts.jsonl'
  'blocks.jsonl'
  'district_panchayats.jsonl'
  'block_panchayats.jsonl'
  'villages.jsonl'
)

cd data > /dev/null
for prefix in ${lgd_file_prefixes[*]}
do
  date_file=${prefix}.lgd_date.txt
  [[ ! -e $date_file ]] || rm $date_file

  lgd_file=lgd/${prefix}.csv
  [[ ! -e $lgd_file ]] || rm $lgd_file
done

for file in ${data_files[*]}
do
  [[ ! -e $file ]] || rm $file
done

cd - > /dev/null

rm -rf apicache
