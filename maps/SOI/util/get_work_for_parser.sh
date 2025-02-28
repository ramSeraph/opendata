#!/bin/bash

gh release download soi-pdfs -p list.txt -O pdfs_list.txt
gh release download soi-tiffs -p list.txt -O tiffs_list.txt

comm <(cat pdfs_list.txt| cut -d" " -f2 | sort) <(cat tiffs_list.txt | cut -d" " -f2 | sort) | cut -f1 | grep "^[0-9]" > $1

rm pdfs_list.txt
rm tiffs_list.txt
