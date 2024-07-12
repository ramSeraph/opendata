#!/bin/bash

# pick a compute instance.. c2-standard-8 instance seems to do the job in 8 hrs
# add a 200GB SSD disk

# locate attached disk
# ls -l /dev/disk/by-id/google-*

# format attached disk, pick disk based on output of above command
# sudo mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/sdb

# mount attached disk
# sudo mkdir -p /mnt/disks/workdir
# sudo mount -o discard,defaults /dev/sdb /mnt/disks/workdir

# prepare disk with data and code
# cd /mnt/disks/workdir/
# sudo chmod 777 .
# git clone https://github.com/ramSeraph/opendata.git
# cd opendata/maps/SOI
# mkdir data
# cd data
# wget https://github.com/ramSeraph/opendata/releases/download/soi-ancillary/index.geojson
# cd -
# mkdir export/gtiffs
# cd exports/gtiffs
# gsutil -m cp gs://soi_data/export/gtiffs/* .
# cd ../..

# install packages
sudo add-apt-repository -y ppa:ubuntugis/ppa
sudo apt-get update
sudo apt-get install ---no-install-recommends -y gdal-bin libgdal-dev python3-venv python3-dev g++
python3 -m venv .venv
source .venv/bin/activate
GDAL_VERSION=$(gdalinfo --version | cut -d"," -f1 | cut -d" " -f2)
sed -i "s/gdal==.*/gdal==${GDAL_VERSION}/g" /requirements.parse.txt
pip3 install -r requirements.parse.txt

# create tiles
mkdir -p export/tiles
nohup python tile.py 2>&1 >log.txt &
tail -f log.txt

# create pmtiles
mkdir temp
export TMPDIR="$(pwd)/temp"
ONLY_DISK=1 python partition.py

# push to github
# install gh
# (type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) && sudo mkdir -p -m 755 /etc/apt/keyrings && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && sudo apt update && sudo apt install gh -y
 
# create a github token with "repo", "org:read" and "workflow" privileges, use it to login with the below command 
# gh auth login

# go to github and manually delete the assets in "soi-latest" tag.
asset_names=$(gh release view soi-latest --json assets --jq '.assets[].name')
for asset_name in $asset_names; do gh release delete-asset soi-latest $asset_name; done

# upload the pmtiles files
cd staging/pmtiles
files=$(ls .)
for file in $files; do gh release upload soi-latest $file; done


