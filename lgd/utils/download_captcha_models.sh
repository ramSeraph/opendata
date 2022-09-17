#!/bin/bash

models_folder=$1

[[ -z $models_folder ]] && echo "Usage $0 <models_dir>" && exit 1

[[ -d $models_folder ]] || mkdir -p $models_folder

cd $models_folder
files=("LICENSE" 'lstm/eng.traineddata' 'lstm/osd.traineddata' 'old/eng.traineddata' 'old/myconfig')

for f in "${files[@]}"
do
   d=$(dirname $f)
   [[ -d $d ]] || mkdir $d
   wget https://storage.googleapis.com/lgd_captcha_tesseract_models/$f -O $f
done


