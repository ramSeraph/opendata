
Contains code to scrape and parse data from [Survey Of India](https://onlinemaps.surveyofindia.gov.in/)

# Open Series Map

## Scraping

Uses google tesseract to break the captchas - https://tesseract-ocr.github.io/tessdoc/Home.html

For mac install tesseract using homebrew
`brew install tesseract`

tested with python version 3.9

python requirements are in the `requirements.txt` file. Run `pip install -r requirements.txt` to install the requirements.

requires usernames and passwords in `data/users.json`

example `users.json`
```
[
    {
        "name": "<username_1>",
        "phone_num": "<10_digit_phone_num_1>",
        "password": "<password_1>",
        "email_id": "<email_id_1>",
        "first_login": false
    },
    {
        "name": "<username_2>",
        "phone_num": "<10_digit_phone_num_2>",
        "password": "<password_2>",
        "email_id": "<email_id_2>",
        "first_login": false
    }
]

```

run following command to pull data:
`python scrape.py`

pdfs for the sheets end up at `data/raw/`


## Parsing

This involves the following steps
* converting the pdfs to images
* dissecting the image into the maparea area, legend area, compilation index area and notes area
* further process map area
    * locate corners and further locate the actual mapbox
    * use the corners and the index file to georeference the mapbox and reproject it to epsg:3857 from UTM 
        and also use the index file to further crop the image
       * use alpha channel for nodata to keep things simple in this stage
    * use of alpha channel leads to big files, so now convert the alpha channel to a nodata internal mask
      and use further compression which now becomes accessible without the alpha channel

The final compressed, clipped, georeferenced file ends up at `export/gtiffs/<sheet_no>.tif`

All intermediate files are at `data/inter/<sheet_no>/`

Depends on `mupdf` for pdf to jpg conversion, `gdal` for georeferencing and the python dependencies are listed in `requirements.parse.txt`

All of this can be triggered using `python parse.py`

By default it runs through all the available files in `data/raw/` and all files which had problems get saved to `data/errors.txt`

Parallelism is exploited where possible - assumes 8 available cpus - my laptop config :)

Reruns ignore already processed files

Environment variables can be used to change behavior
* `SHOW_IMG=1` displays the image processing steps on the terminal using `imgcat`
* `ONLY_CONVERT=1` can be used to only do the pdf to image conversion parallely for better cpu saturation
* `FROM_LIST=<filename>` can be used to only parse files listed in `<filename>`, this also errors out on first failure


## Tiling

`python tile.py` to tile

Tiles get created at `export/tiles`, also generates an auxilary `export/prev_files_to_tile.json` which contains the list of sheet files that went in and their modification times

Rerunning `python tile.py` picks up any new/modified sheet files in `export/gtiffs` and does an incremetal retitling operation

This is still slow and requires the presence of all the previous tiling data,
So a newer retiling script was created to just pull the requisite tiles from the original tiles into a staging area, retile and push back only the affected tiles into the main area.

Invoke with `python retile.py`.. for now expects a `retile.txt` file containing just the sheet names to retile

## Update Jobs

Update jobs are run with github actions on a weekly basis
Data ends up at google cloud storage `soi_data` bucket

# Village boundaries

## Scraping

Most directions/software requirements same as for Open Series Maps, except the final commands

run following command to pull data:
`python scrape_villages.py`

shapefile zips end up at `data/raw/villages/`

To recover from intermittent errors, run
`FORCE=1 python scrape_villages.py`

To force rechecking previously missing Districts, run
`FORCE=1 FORCE_UNAVAILABLE=1 python scrape_villages.py`

To enter captcha manually and not depend on auto captch breaking, run `CAPTCHA_MANUAL=1 python scrape_bounds.py`

uses `imgcat` for displaying the captcha, which might work on some terminals.

The python requirements for the scraping part are captured in `requirements.txt`

To convert the resulting shapefiles to OSM xml files which can be directly used in JOSM, run 
`python convert_villages.py`

this requires an extra python dependency of `pytopojson==1.1.2` and an extra software dependency on `gdal`

the resulting per tehsil `.osm` files end up in corresponding district folders in `data/raw/villages/` 


