#!/bin/bash

token="$(cat auth_token.txt)"

bucket="soi_data"
prefix="export/tiles/"
out_file="to_fix_objs.txt"

base_url="https://storage.googleapis.com/storage/v1/b/${bucket}/o?prefix=${prefix}&maxResults=5000"
done_count=0
while true; do
    url="$base_url"
    if [[ -e page_token.txt ]]; then
        url="${base_url}&&pageToken=$(cat page_token.txt)"
    fi
    curl "$url" > resp.json
    cat resp.json| jq -r '.nextPageToken' > page_token.txt
    got="$(cat resp.json | jq -r '.items | length')"
    done_count=$(( done_count + got ))
    cat resp.json | jq -r '.items[] | select(.contentType!="image/webp") | .name' >> $out_file
    to_fix=$( wc -l $out_file )
    echo "done: ${done_count} to_fix: ${to_fix}"
    rm resp.json
    if [[ $got < 5000 ]]; then
        break;
    fi
done
