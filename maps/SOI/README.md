
Contains code to scrape and parse data from [Survey Of India](https://onlinemaps.surveyofindia.gov.in/)

# Scraping

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
}

```

run following command to pull data:
`python scrape.py`

pdfs for the sheets end up at `data/raw/`


# Parsing

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

The final compressed, clipped, georeferenced file ends up at 'export/gtiffs/<sheet_no>.tif`
all intermediate files are at `data/inter/<sheet_no>/`

Depends on `mupdf` for pdf to jpg conversion. and the python dependencies are listed in `requirements.parse.txt`

All of this can be triggered using `python parse.py`

By default it runs through all the available files in `data/raw/` and all files which had problems get saved to `data/errors.txt`
Parallelism is exploited where possible - assumes 8 available cpus - my laptop config :)
Reruns ignore already processed files

Environment variables can be used to change behavior
`SHOW_IMG=1` displays the image processing steps on the terminal using `imgcat`
`ONLY_CONVERT=1` can be used to only do the pdf to image conversion parallely for better cpu saturation
`ONLY_FAILED=1` can be used to only execute failed files listed in `data/errors.txt`, this also errors out on first failure


# Tiling

`python tile.py` to tile

Tiles get created at `export/tiles`, also generates an auxilary `export/prev_files_to_tile.json` which contains the list of sheet files that went in and their modification times

Rerunning `python tiles.py` picks up any any new/modified sheet files in `export/gtiffs` and does a incremetal retitling operation

This is still slow and requires the presence of all the previous tiling data, So a newer retiling script was created to just pull the requisite tiles from the original tiles into a staging area, retile and push back only the affected tiles into the main area.

Invoke with `python retile.py` .. for now expects a `retile.txt` file containing just the sheet names to retile 

# Update Jobs

Update jobs are run with github actions on a weekly basis
Data ends up at google cloud storage `soi_data` bucket
