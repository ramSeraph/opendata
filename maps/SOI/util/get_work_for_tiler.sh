#!/bin/bash

gh release download soi-tiffs -p list.txt -O tiffs_list.txt --clobber
gh release download soi-tiffs -p tiled_list.txt -O tiled_list.txt --clobber

comm <(cat tiffs_list.txt| cut -d" " -f2 | sort) <(cat tiled_list.txt | cut -d" " -f2 | sort) | cut -f1 | grep "^[0-9]" > $1

rm tiffs_list.txt tiled_list.txt
