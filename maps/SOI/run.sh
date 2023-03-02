#!/bin/bash

PLATFORM=${PLATFORM:-"linux/amd64"}

if [ "$BUILD" == "1" ]; then
	docker build --platform linux/amd64 --build-arg build_type=final -f Dockerfile -t soi .
fi

DOCKER_CMD="docker run --platform $PLATFORM --rm --env SHOW_IMG=1 -v $PWD:/code -w /code/ -it --name soi_run soi" 

if [ "$SETUP" == "1" ]; then
    $DOCKER_CMD python -m venv /code/.venv
    $DOCKER_CMD pip install --upgrade pip
fi

$DOCKER_CMD "${@}"
