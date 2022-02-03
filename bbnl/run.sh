#!/bin/bash

PLATFORM=${PLATFORM:-"linux/amd64"}

if [ $BUILD == "1" ]; then
	docker build --platform linux/amd64 -f Dockerfile -t bbnl .
fi

docker run --platform $PLATFORM --rm  -v "$PWD":/code -w /code/ -it bbnl "${@}"
