#!/bin/bash

gh release download soi-pdfs -p list.txt -O pdfs_list.txt --clobber
gh release download soi-tiffs -p list.txt -O tiffs_list.txt --clobber

comm <(cat pdfs_list.txt| cut -d" " -f2 | sort) <(cat tiffs_list.txt | cut -d" " -f2 | sort) | cut -f1 | grep "^[0-9]" > temp.txt

uv run python -c "from known_problems import known_problems as kp; l = [ k.replace('data/raw/', '').replace('.pdf', '') for k in  kp ]; print('\n'.join(l) + '\n')" > kp.txt

comm <(cat temp.txt | sort) <(cat kp.txt | sort)  | cut -f1 | grep "^[0-9]" > $1

rm pdfs_list.txt tiffs_list.txt temp.txt kp.txt
