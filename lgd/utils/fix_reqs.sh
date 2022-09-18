#!/bin/bash

PLATFORM=${PLATFORM:-"linux/amd64"}
PLATFORM_ARG=""
if [[ ! -z "$PLATFORM" ]]; then
    PLATFORM_ARG="--platform $PLATFORM"
fi

img="lgd-req"
docker build --build-arg build_type=req-build $PLATFORM_ARG . -t $img

run_args="$PLATFORM_ARG -v $(pwd):/code -v $(pwd)/.venv:/venv -w /code -it --rm $img"

docker run $run_args python -m venv /venv
docker run $run_args /venv/bin/pip install pip-tools
docker run $run_args /venv/bin/pip-compile requirements.in
