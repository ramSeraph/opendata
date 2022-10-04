#!/bin/bash

GITHUB_REPOSITORY=${GITHUB_REPOSITORY:-""}
if [[ -z "$GITHUB_REPOSITORY" ]]; then
    exit 1
fi

gh_headers="Accept: application/vnd.github+json" 
curr_time=$(date +%s)

err_file=${CACHE_ERR_FILE:-"cache_err_file.txt"} 
touch $err_file

function record_call {
    echo ${FUNCNAME[*]} "$@" >> $err_file
}


function get_cache_info {
    record_call
    gh api -H "$gh_headers" "/repos/${GITHUB_REPOSITORY}/actions/caches" 2>>$err_file
}

function get_old_ids {
    match="$1"
    older_than_in_days="$2"

    cutoff=$(echo $curr_time - 86400*$older_than_in_days | bc -l)
    cutoff=$( echo ${cutoff}/1 | bc )

    ids="$(get_cache_info | jq --arg c "$cutoff" --arg f "$match" '.actions_caches[] | select(.last_accessed_at | sub("\\.[0-9]+Z$";"Z") | fromdateiso8601 < ($c | tonumber)) | select(.key | test($f)) | .id' 2>>$err_file)"
    echo $ids
}

function delete_cache_by_ids {
    record_call "$@"
    echo
    echo "deleting ids $@"
    for cache_id; do
        echo "Clearing cache $cache_id"
        gh api --method DELETE -H "$gh_headers" /repos/${GITHUB_REPOSITORY}/actions/caches/${cache_id}
    done
}


function delete_caches {
    record_call "$@"
    match="$1"
    if [[ -z "$1" ]]; then
        echo "match param missing" >> $err_file
        exit 1
    fi
    older_than_in_days="$2"
    if [[ ! "$older_than_in_days" =~ ^[0-9\.]+$ ]]; then
        echo "older_than_in_days param $older_than_in_days is not a positive number" >> $err_file
        exit 1
    fi
    old_ids="$(get_old_ids "$match" "$older_than_in_days" | tr '\n' ' ')"
    echo "old caches to delete: $old_ids"
    delete_cache_by_ids $old_ids
}
