#!/bin/bash

PLATFORM=${PLATFORM:-"linux/amd64"}

if [ "$BUILD" == "1" ]; then
	docker build --platform linux/amd64 -f Dockerfile -t soi .
fi

DOCKER_CMD="docker run --platform $PLATFORM --rm  -v $PWD:/code -w /code/ -it --name soi_run soi" 

if [ "$SETUP" == "1" ]; then
    $DOCKER_CMD python -m venv /code/.venv                                                                                                                                              master ✱ ◼
    $DOCKER_CMD pip install --upgrade pip
fi

$DOCKER_CMD "${@}"
