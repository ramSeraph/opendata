#!/bin/bash


cat to_fix_objs.txt | xargs -I {} gsutil setmeta -h "Content-Type:image/webp" gs://soi_data/{}

