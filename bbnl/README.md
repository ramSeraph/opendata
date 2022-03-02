
Code to scrape and parse data from Bharat Broadband Network Limited site - https://bbnl.nic.in/

Tested with python version 3.9.4

Python requirements are in the `requirements.txt` file. Run `pip install -r requirements.txt` to install the requirements.

Alternatively use the `Dockerfile` to run using `run.sh`

`./run.sh python scrape.py <args>`


```
usage: scrape.py [-h] [-c COMP [COMP ...]] [-n NO_COMP [NO_COMP ...]] [-a ACTION [ACTION ...]] [-p NUM_PARALLEL] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

optional arguments:
  -h, --help            show this help message and exit
  -c COMP [COMP ...], --comp COMP [COMP ...]
                        component to work on, should be one of dict_keys(['active_gps', 'status_active_gps', 'block_connected_gps', 'block_graphs', 'locations', 'implementers', 'panchayats',
                        'planned_nofn'])
  -n NO_COMP [NO_COMP ...], --no-comp NO_COMP [NO_COMP ...]
                        component to skip, should be one of dict_keys(['active_gps', 'status_active_gps', 'block_connected_gps', 'block_graphs', 'locations', 'implementers', 'panchayats',
                        'planned_nofn'])
  -a ACTION [ACTION ...], --action ACTION [ACTION ...]
                        action to execute, one of ['list', 'scrape', 'parse']
  -p NUM_PARALLEL, --num-parallel NUM_PARALLEL
                        number of parallel processes to use
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level
```


Sample Usage:

`./run.sh python scrape.py -l INFO -c status_active_gps -p 10`

This is a WIP.
