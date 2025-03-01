#!/bin/bash

work_file=$1

cat $work_file | xargs -I {} bash -c "[[ -e data/raw/{}.pdf ]] || echo {}" > to_download.txt
cat to_download.txt | xargs -I {} gh release download soi-pdfs -p {}.pdf -O data/raw/{}.pdf
rm to_download.txt
