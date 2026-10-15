
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

The current active components are listed below. Run `python -m scrape -m COMPS`
for their descriptions and fields.

| Component | Output file |
| --- | --- |
| `BLOCKS` | `blocks.csv` |
| `BLOCK_VILLAGES` | `villages_by_blocks.csv` |
| `CENTRAL_ADMIN_DEPTS` | `central_admin_depts.csv` |
| `CENTRAL_ORG_DESIGNATIONS` | `central_org_designations.csv` |
| `CENTRAL_ORG_DETAILS` | `central_orgs.csv` |
| `CENTRAL_ORG_UNITS` | `central_org_units.csv` |
| `CONSTITUENCIES_ASSEMBLY` | `assembly_constituencies.csv` |
| `CONSTITUENCIES_MAPPINGS_URBAN` | `constituencies_mapping_urban.csv` |
| `CONSTITUENCIES_PARLIAMENT` | `parliament_constituencies.csv` |
| `CONSTITUENCY_COVERAGE` | `constituency_coverage.csv` |
| `DISTRICTS` | `districts.csv` |
| `DISTRICT_PANCHAYATS` | `district_panchayats.csv` |
| `INVALIDATED_VILLAGES` | `invalidated_census_villages.csv` |
| `PANCHAYAT_MAPPINGS` | `gp_mapping.csv` |
| `PINCODE_URBAN` | `pincode_urban.csv` |
| `PINCODE_VILLAGES` | `pincode_villages.csv` |
| `PRI_LOCAL_BODIES` | `pri_local_bodies.csv` |
| `PRI_LOCAL_BODY_WARDS` | `pri_local_body_wards.csv` |
| `STATES` | `states.csv` |
| `STATE_ADMIN_DEPTS` | `state_admin_depts.csv` |
| `STATE_ORG_DESIGNATIONS` | `state_org_designations.csv` |
| `STATE_ORG_DETAILS` | `state_orgs.csv` |
| `STATE_ORG_UNITS` | `state_org_units.csv` |
| `SUB_DISTRICTS` | `subdistricts.csv` |
| `TLB_VILLAGES` | `tlb_villages.csv` |
| `TRADITIONAL_LOCAL_BODIES` | `traditional_local_bodies.csv` |
| `TRANSACTIONS` | `transactions.csv` |
| `URBAN_LOCAL_BODIES` | `urban_local_bodies.csv` |
| `URBAN_LOCAL_BODIES_COVERAGE` | `statewise_ulbs_coverage.csv` |
| `URBAN_LOCAL_BODY_WARDS` | `urban_local_body_wards.csv` |
| `VILLAGES` | `villages.csv` |

`CHANGES` is no longer an active downloader. Its historical `changes.csv` remains
available; the replacement report is collected separately as `TRANSACTIONS`.

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
