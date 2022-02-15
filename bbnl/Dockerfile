FROM python:3.9.4

RUN apt-get update; apt-get install -y --no-install-recommends poppler-utils poppler-data
RUN apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6
#RUN apt-get install -y --no-install-recommends ghostscript python3-tk

RUN mkdir /code

COPY requirements.txt /code/requirements.txt

RUN pip install -r /code/requirements.txt

RUN apt-get install -y --no-install-recommends libgs-dev

RUN pip install imgcat matplotlib 
