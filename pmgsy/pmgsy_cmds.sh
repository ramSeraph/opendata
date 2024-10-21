#!/bin/bash

set -x
# get master data

#mkdir -p data/raw
#mkdir -p data/parsed
#wget -O data/raw/MasterData.xls https://github.com/datameet/pmgsy-geosadak/raw/master/data/MasterData.xls
#python convert.py

date_str='20Oct2024'

function download_stuff {
    raw_dir=data/raw/${date_str}/${folder}
    parsed_dir=data/parsed/${date_str}/${folder}
    mkdir -p $raw_dir
    #cat $state_zip_list | xargs -I {} wget -O $raw_dir/{} https://github.com/datameet/pmgsy-geosadak/raw/master/data/${folder}/{}
    mkdir -p $parsed_dir/shps
    find $raw_dir | grep zip | cut -d"." -f1 | cut -d"/" -f5 | xargs -I {} 7z -o${parsed_dir}/shps/{} x $raw_dir/{}.zip
    mkdir -p $parsed_dir/geojsons

    find $parsed_dir/shps -type d -depth 1 | cut -d"/" -f6 | \
    while read -r state
    do
        echo $state
        zip_file=$(find $parsed_dir/shps/$state/*.zip 2>/dev/null)
        if [[ $zip_file != '' ]]; then
            7z -o$parsed_dir/shps/$state x $zip_file
            rm $zip_file
        fi
        shp_file=$(find $parsed_dir/shps/$state/*.shp 2>/dev/null)
        prj_file=${shp_file%.shp}.prj
        ogr2ogr -f GeoJSONSeq -s_srs $prj_file -t_srs EPSG:4326 $parsed_dir/geojsons/$state.geojsonl $shp_file
    done
}


# get habitation data
folder='Habitation'
state_zip_list=state_zips.txt
download_stuff
#
# get block boundaries
#folder='Bound_Block'
#state_zip_list=state_zips.txt
#download_stuff

#folder='Facilities'
#state_zip_list=state_zips.txt
#download_stuff

#folder='Road_DRRP'
#state_zip_list=state_zips_drrp.txt
#download_stuff

#folder='Proposals'
#state_zip_list=state_zips.txt
#download_stuff
#python validate.py
