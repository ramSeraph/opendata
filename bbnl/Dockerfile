FROM python:3.9.4

RUN apt-get update; apt-get install -y --no-install-recommends poppler-utils poppler-data libgs-dev ffmpeg libsm6 libxext6

RUN mkdir /code

COPY requirements.txt /code/requirements.txt

RUN pip install -r /code/requirements.txt
