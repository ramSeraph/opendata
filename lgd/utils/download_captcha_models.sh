#!/bin/bash

models_folder=$1

[[ -z $models_folder ]] && echo "Usage $0 <models_dir>" && exit 1

[[ -d $models_folder ]] || mkdir -p $models_folder

cd $models_folder
files=('lstm_eng.traineddata' 'lstm_osd.traineddata' 'old_eng.traineddata' 'old_myconfig')

mkdir lstm
mkdir old

for f in "${files[@]}"
do
   wget https://github.com/ramSeraph/opendata/releases/download/tesseract-models/$f
done

mv lstm_eng.traineddata lstm/eng.traineddata
mv lstm_osd.traineddata lstm/osd.traineddata

mv old_eng.traineddata old/eng.traineddata
mv old_myconfig old/myconfig
