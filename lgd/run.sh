#!/bin/bash

PLATFORM=${PLATFORM:-"linux/amd64"}
PLATFORM_ARG=""
if [[ ! -z "$PLATFORM" ]]; then
    PLATFORM_ARG="--platform $PLATFORM"
fi
img="lgd"
BUILD=${BUILD:-"0"}
if [[ "$BUILD" == "1" ]]; then
    docker build --build-arg build_type=final $PLATFORM_ARG . -t $img
fi

run_args="$PLATFORM_ARG -v $(pwd):/code -w /code -it --rm $img"

docker run $run_args "${@}"
