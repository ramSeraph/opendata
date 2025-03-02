import os
import logging

from pathlib import Path

import requests

from bs4 import BeautifulSoup

base_url = 'https://onlinemaps.surveyofindia.gov.in/'

data_dir = 'data/'
raw_data_dir = data_dir + 'raw/'

session = requests.session()
PROXY_URL = os.environ.get('PROXY_URL', None)
if PROXY_URL is not None:
    session.proxies = {'https': PROXY_URL, 'http': PROXY_URL}

def setup_logging(log_level):
    from colorlog import ColoredFormatter
    formatter = ColoredFormatter("%(log_color)s%(asctime)s [%(levelname)-5s][%(process)d][%(threadName)s] %(message)s",
                                 datefmt='%Y-%m-%d %H:%M:%S',
	                             reset=True,
	                             log_colors={
	                             	'DEBUG':    'cyan',
	                             	'INFO':     'green',
	                             	'WARNING':  'yellow',
	                             	'ERROR':    'red',
	                             	'CRITICAL': 'red',
	                             },
	                             secondary_log_colors={},
	                             style='%')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(level=log_level, handlers=[handler])


def get_page_soup(url):
    resp = session.get(url)
    if not resp.ok:
        raise Exception(f'unable to retrieve {url}')
    soup = BeautifulSoup(resp.text, 'html.parser')
    return soup


def get_page_soup_post(url, data, headers):
    resp = session.post(url, data=data, headers=headers)
    if not resp.ok:
        raise Exception(f'unable to post to {url}')
    soup = BeautifulSoup(resp.text, 'html.parser')
    return soup


def get_form_data(soup):
    form = soup.find('form', {'id': 'masterform'})
    inputs = form.find_all('input')
    form_data = {}
    for inp in inputs:
        t = inp.attrs.get('type', None)
        if t != 'hidden':
            continue
        k = inp.attrs['name']
        v = inp.attrs.get('value', None)
        form_data[k] = v
    form_data['__EVENTARGUMENT'] = ''
    form_data['__LASTFOCUS'] = ''

    return form_data

def ensure_dir(filename):
    Path(filename).parent.mkdir(exist_ok=True, parents=True)

