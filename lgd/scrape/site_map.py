import re
import json
import logging

from pprint import pformat
from pathlib import Path

from bs4 import BeautifulSoup

from .base import BASE_URL

logger = logging.getLogger(__name__)

def collapse_spaces(s):
    return " ".join(s.split())

def get_download_directory_lists(ctx):
    out_arr = []
    download_dir_url = '{}/downloadDirectory.do?OWASP_CSRFTOKEN={}'.format(BASE_URL, ctx.csrf_token)
    req_args = ctx.params.request_args()
    web_data = ctx.session.get(download_dir_url, **req_args)
    if not web_data.ok:
        raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))
    soup = BeautifulSoup(web_data.text, 'html.parser')
    div = soup.find('div', {'id': 'DFD'})
    select = div.find('select', {'id': 'rptFileName'})
    opt_groups = select.find_all('optgroup')
    orig_keys = ('Download Directory',)
    for opt_group in opt_groups:
        label = opt_group.attrs['label'].strip()
        label = collapse_spaces(label)
        curr_keys = orig_keys + (label,)
        options = opt_group.find_all('option')
        for option in options:
            keys = curr_keys + (option.text.strip(),)
            out_arr.append(list(keys))
        if len(options) == 0:
            out_arr.append(list(curr_keys))
    return out_arr


def populate_map(elem, main_arr, keys, main=False):
    search = [ 'ol', 'div' ] if main else [ 'ol' ] 
    a = elem.find('a', recursive=False)
    if a is not None:
        k = a.text.strip()
        k = collapse_spaces(k)
        keys = keys + (k,)
        if 'href' in a.attrs:
            #main_map[keys] = { 'href': a.attrs['href'] }
            main_arr.append(list(keys))
        elif 'param' in a.attrs:
            #main_map[keys] = { 'param': a.attrs['param'], 'id': a.attrs['id'] }
            main_arr.append(list(keys))
        else:
            raise Exception('Unexpected link {a}')
    else:
        if elem.name != 'div':
            desc = elem.find('b', recursive=False)
            k = desc.text.strip()
            k = collapse_spaces(k)
            keys = keys + (k,)

    ols = elem.find_all(search, recursive=False)
    for ol in ols:
        if ol.name == 'div':
            heading = ol.text.strip()
            heading = collapse_spaces(heading)
            keys = (heading,)
            continue
        lis = ol.find_all('li', recursive=False)
        for li in lis:
            populate_map(li, main_arr, keys)



def get_report_lists(ctx):
    main_arr = []
    reports_url = '{}/welcome.do?OWASP_CSRFTOKEN={}'.format(BASE_URL, ctx.csrf_token)
    req_args = ctx.params.request_args()
    web_data = ctx.session.get(reports_url, **req_args)
    if not web_data.ok:
        raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))
    soup = BeautifulSoup(web_data.text, 'html.parser')
    div = soup.find('div', {'id': 'reports-model'})

    title_header = div.find('h4', {'class': 'modal-title'})
    heading = title_header.text.strip()
    heading = collapse_spaces(heading)
    keys = (heading,)
    div_body = div.find('div', {'class': 'modal-body'})
    populate_map(div_body, main_arr, keys, main=True)
    return main_arr


def get_sitemap(ctx):
    full_arr = []
    dd_arr = get_download_directory_lists(ctx)
    full_arr.extend(dd_arr)
    rp_arr = get_report_lists(ctx)
    full_arr.extend(rp_arr)
    logger.info(pformat(full_arr))
    full_arr = [ [ re.sub(' +', ' ', t) for t in k ] for k in full_arr ]
    return full_arr

def get_known_site_map():
    known_site_map_file = Path(__file__).parent / 'site_map.json'
    with open(known_site_map_file, 'r') as f:
        known_site_map = json.load(f)
    return known_site_map


def get_changes_in_site_map(known, scraped):
    known_map = {}
    for e in known:
        k = tuple(e["dropdown"])
        known_map[k] = e

    old_keys = set(known_map.keys())
    new_keys = set([ tuple(e) for e in scraped ])

    missing_in_new = new_keys - old_keys
    missing_in_old = old_keys - new_keys

    missing_in_new = [ list(k) for k in missing_in_new ]
    missing_in_old = [ list(k) for k in missing_in_old ]

    return {
        "removed": missing_in_old,
        "added": missing_in_new
    }

