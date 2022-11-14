#!/bin/bash

if [[ "$1" == "parse" ]]; then
    img="parser-req"
    dfile="Dockerfile.parse"
    venv_dir=".venv_parser"
    req_out="requirements.parse.txt"
    req_in="requirements.parse.in"
else
    img="scraper-req"
    dfile="Dockerfile"
    venv_dir=".venv"
    req_out="requirements.txt"
    req_in="requirements.in"
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PAR_DIR="$(dirname $SCRIPT_DIR)"

cd $PAR_DIR

PLATFORM=${PLATFORM:-"linux/amd64"}
PLATFORM_ARG=""
if [[ ! -z "$PLATFORM" ]]; then
    PLATFORM_ARG="--platform $PLATFORM"
fi

docker build --build-arg build_type=req-build $PLATFORM_ARG . -f $dfile -t $img

run_args="$PLATFORM_ARG -v $(pwd):/code -v $(pwd)/${venv_dir}:/venv -w /code -it --rm $img"

docker run $run_args python -m venv /venv
docker run $run_args /venv/bin/pip install pip-tools
docker run $run_args /venv/bin/pip-compile $req_in --output-file $req_out
