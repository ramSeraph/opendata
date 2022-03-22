
Contains code to scrape and parse data from Local Government Directory site - https://lgdirectory.gov.in

Has code to to pull data from Download Directory Section and the Reports section. Can be extended to pull data from anywhere on that site.

Uses google tesseract to break the captchas - https://tesseract-ocr.github.io/tessdoc/Home.html

For mac install tesseract using homebrew
`brew install tesseract`

tested with python version 3.9

python requirements are in the `requirements.txt` file. Run `pip install -r requirements.txt` to install the requirements.

captcha/ folder has code for the captcha breaking and also some test captcha images

For mac m1 users extra commands needed to set things up are in `m1.help` file.

Run `python -m scrape <args>` from the lgd directory to pull data.

Typical invocation `python -m scrape -m RUN -p 10 -l INFO -R 300`

Individual components can be downloaded by running `python -m scrape -m RUN --comp <comp_name>`

list of components can be retrieved using `python -m scrape -m COMPS`

to get list of possible arguments run `python -m scrape -h`
```
usage: __main__.py [-h] [-m {COMPS,DEPS,RUN}] [-c COMP [COMP ...]] [-N NO_COMP [NO_COMP ...]] [-R READ_TIMEOUT] [-C CONNECT_TIMEOUT] [-s VERIFY_SSL] [-r HTTP_RETRIES] [-b] [-P] [-H] [-A] [-F]
                   [-p PARALLEL] [-D BASE_RAW_DIR] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

optional arguments:
  -h, --help            show this help message and exit
  -m {COMPS,DEPS,RUN}, --mode {COMPS,DEPS,RUN}
                        mode to run script in,
                        	COMPS: Get list of all components
                        	DEPS: Get dependencies between components
                        	RUN: Download all things (default: Mode.RUN)
  -c COMP [COMP ...], --comp COMP [COMP ...]
                        component to select, no choice implies all
                        get list of components by running this script with COMPS mode argument (default: [])
  -N NO_COMP [NO_COMP ...], --no-comp NO_COMP [NO_COMP ...]
                        component to deselect
                        get list of components by running this script with COMPS mode argument (default: [])
  -R READ_TIMEOUT, --read-timeout READ_TIMEOUT
                        http read timeout in secs (default: 60)
  -C CONNECT_TIMEOUT, --connect-timeout CONNECT_TIMEOUT
                        http connect timeout in secs (default: 10)
  -s VERIFY_SSL, --verify-ssl VERIFY_SSL
                        verify ssl for connections (default: True)
  -r HTTP_RETRIES, --http-retries HTTP_RETRIES
                        number of times to retry on http failure (default: 3)
  -b, --progress-bar    show progress bar (default: False)
  -P, --print-captchas  print captchas on failure (default: False)
  -H, --save-failed-html
                        save html for failed requests (default: False)
  -A, --save-all-captchas
                        save all captchas encountered (default: False)
  -F, --save-failed-captchas
                        save all captchas which we failed for (default: False)
  -p PARALLEL, --parallel PARALLEL
                        number of parallel downloads (default: 1)
  -D BASE_RAW_DIR, --base-raw-dir BASE_RAW_DIR
                        directory to write data to, will be created if it doesn't exist (default: data/raw)
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level (default: INFO)
```


`python -m scrape -h` for help

This is a WIP.
