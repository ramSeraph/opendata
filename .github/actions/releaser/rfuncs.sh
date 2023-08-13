
err_file=${ERR_FILE:-"err_file.txt"} 
touch $err_file

function record_call {
    echo ${FUNCNAME[*]} "$@" >> $err_file
}

function get_release_id {
    record_call "$@"
    tname=$1
    release_id="$(gh api -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases 2>>$err_file | jq --arg tname $tname '.[] | select( .tag_name == $tname) | .id' 2>>$err_file)"
    echo $release_id
}

function has_release {
    record_call "$@"
    rid="$(get_release_id $1)"
    if [[ "$rid" == "" ]]; then 
        echo "no"
    else
        echo "yes"
    fi
}

function move_release {
    record_call "$@"
    from_id=$1
    to=$2
    to_name="$3"
    gh api --method PATCH -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases/$from_id -f tag_name="$to" -f name="$to_name" 2>>$err_file
}

function delete_release {
    record_call "$@"
    rid=$1
    gh api --method DELETE -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases/$rid
}

function download_release_assets {
    record_call "$@"
    from_id=$1
    out_dir=$2

    lines=$(gh api -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases/${from_id}/assets 2>>$err_file | jq -r '.[] | "\(.id),\(.name)"')
    for line in $(echo $lines)
    do
        id=$(echo $line | awk '{split($0,a,","); print a[1]}')
        name=$(echo $line | awk '{split($0,a,","); print a[2]}')
        echo "downloading $name"
        gh api -H "Accept: application/octet-stream" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases/assets/$id > ${out_dir}/${name}
    done
}
