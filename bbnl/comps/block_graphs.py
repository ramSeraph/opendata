import logging

from pathlib import Path
import requests

from .common import (get_url, get_page_soup,
                     get_links_from_map_page,
                     ensure_dir, drill_down_and_download,
                     get_forward_url)

logger = logging.getLogger(__name__)


def get_block_graphs(executor, url):
    main_page_url = 'https://bbnl.nic.in'
    web_data = requests.get(main_page_url)
    if not web_data.ok:
        raise Exception(f'unable to get page {main_page_url}')

    cookies = web_data.headers['Set-Cookie']
    cookie = cookies.split(';')[0]
    headers = {
        'Cookie': cookie
    }
    fwd_url = get_forward_url(get_url(url))
    logger.info(f'got forwarded url: {fwd_url}')
    soup = get_page_soup(fwd_url, headers=headers)
    map_infos = get_links_from_map_page(soup)
    for map_info in map_infos:
        drill_down_and_download(map_info, headers, 'block_graphs')
        

def parse_block_graphs(executor):
    pass


#TODO: get last update times


