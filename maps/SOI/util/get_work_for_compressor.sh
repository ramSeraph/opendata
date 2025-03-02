#!/bin/bash

gh release download soi-pdfs -p list.txt -O pdfs_list.txt --clobber
wget https://storage.googleapis.com/soi_data/compressed/list.txt -O jpgs_list.txt

comm <(cat pdfs_list.txt| cut -d" " -f2 | sort) <(cat jpgs_list.txt | sort) | cut -f1 | grep "^[0-9]" > temp.txt

uv run python -c "from known_problems import known_problems as kp; l = [ k.replace('data/raw/', '').replace('.pdf', '') for k in  kp ]; print('\n'.join(l))" > kp.txt

comm <(cat temp.txt | sort) <(cat kp.txt | sort)  | cut -f1 | grep "^[0-9]" > $1

rm jpgs_list.txt pdfs_list.txt temp.txt kp.txt
