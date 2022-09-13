
gh_headers="Accept: application/vnd.github+json" 

err_file=${ERR_FILE:-"err_file.txt"} 
touch $err_file

function record_call {
    echo ${FUNCNAME[*]} "$@" >> $err_file
}

function get_release_id {
    record_call "$@"
    set +e
    release_id="$(gh api -H "$gh_headers" /repos/${GITHUB_REPOSITORY}/releases/tags/$1 2>>$err_file | jq '.id' 2>>$err_file)"
    set -e
    echo $release_id
}

function has_release {
    record_call "$@"
    export rname=$1
    release_names="$(gh api -H "$gh_headers" /repos/${GITHUB_REPOSITORY}/releases 2>>$err_file | jq -r '.[].name' 2>>$err_file)"
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
    gh api --method PATCH -H "$gh_headers" /repos/${GITHUB_REPOSITORY}/releases/$from_id -f tag_name="$to" -f name="$to" 2>>$err_file
    gh api --method DELETE -H "$gh_headers" /repos/${GITHUB_REPOSITORY}/git/refs/tags/${from} 2>>$err_file
}
