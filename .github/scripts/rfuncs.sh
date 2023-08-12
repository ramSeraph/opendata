
err_file=${ERR_FILE:-"err_file.txt"} 
touch $err_file

function record_call {
    echo ${FUNCNAME[*]} "$@" >> $err_file
}

function get_release_id {
    record_call "$@"
    set +e
    release_id="$(gh api -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases/tags/$1 2>>$err_file | jq '.id' 2>>$err_file)"
    set -e
    echo $release_id
}

function has_release {
    record_call "$@"
    export rname=$1
    release_names="$(gh api -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases 2>>$err_file | jq -r '.[].name' 2>>$err_file)"
    set +e
    echo "$release_names" | grep -q "^$rname$" 2>>$err_file
    if [[ $? == 0 ]]; then
        echo "yes"
    else
        echo "no"
    fi
    set -e
}

function move_release {
    record_call "$@"
    export from_id=$1
    export from=$2
    export to=$3
    gh api --method PATCH -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28"  /repos/${GITHUB_REPOSITORY}/releases/$from_id -f tag_name="$to" -f name="$to" 2>>$err_file
    gh api --method DELETE -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/git/refs/tags/${from} 2>>$err_file
}

function download_release_assets {
    record_call "$@"
    export from_id=$1
    export out_dir=$2

    lines=$(gh api -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases/${from_id}/assets 2>>$err_file | jq -r '.[] | "\(.id),\(.name)"')
    for line in $(echo $lines)
    do
        id=$(echo $line | awk '{split($0,a,","); print a[1]}')
        name=$(echo $line | awk '{split($0,a,","); print a[2]}')
        echo "downloading $name"
        gh api -H "Accept: application/octet-stream" -H "X-GitHub-Api-Version: 2022-11-28" /repos/${GITHUB_REPOSITORY}/releases/assets/$id > ${out_dir}/${name}
    done

}
