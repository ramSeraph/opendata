import json
import requests
import logging

from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

from bs4 import BeautifulSoup
from dictdiffer import diff

from comps.common import ensure_dir
from comps.active_gps import get_active_gps, parse_active_gps
from comps.status_active_gps import get_status_active_gps, parse_status_active_gps
from comps.block_connected_gps import get_block_connected_gps, parse_block_connected_gps
from comps.block_graphs import get_block_graphs, parse_block_graphs
from comps.locations import get_locations, parse_locations
from comps.implementers import get_implementers, parse_implementers
from comps.panchayats import get_panchayats, parse_panchayats
from comps.planned_nofn import get_planned_nofn, parse_planned_nofn


logger = logging.getLogger(__name__)

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

    for mod_name in ['pdfminer.pdfinterp', 'pdfminer.pdfpage', 'pdfminer.pdfdocument']:
        _logger = logging.getLogger(mod_name)
        _logger.setLevel(logging.WARNING)

comp_map = {
    'active_gps': {
        'desc': 'All Service Ready Gram Panchayats',
        'filename': 'active_gps.csv',
        'scrape': get_active_gps,
        'parse': parse_active_gps
    },
    'status_active_gps': {
        'desc': 'Status Of Active Gram Panchayats',
        'filename': 'status_active_gps.csv',
        'scrape': get_status_active_gps,
        'parse': parse_status_active_gps
    },
    'block_connected_gps': {
        'desc': 'List of Gram Panchayats where fiber of BBNL is available up to the Blocks from the GPs',
        'filename': 'block_connected_gps.csv',
        'scrape': get_block_connected_gps,
        'parse': parse_block_connected_gps
    },
    'block_graphs': {
        'desc': 'Block wise line diagrams for BharatNet and BBNL dark fiber',
        'filename': 'block_graphs.json',
        'scrape': get_block_graphs,
        'parse': parse_block_graphs
    },
    'locations': {
        'desc': ['Lat-Long of GPs under BharatNet Phase-I', 'Lat-Long of FPOIs for GPs under BharatNet Phase-I', 'Lat-Long of OLTs for GPs under BharatNet Phase-I'],
        'filename': [ 'GP_locations.csv', 'FPOI_locations.csv', 'OLT_locations.csv' ],
        'scrape': get_locations,
        'parse': parse_locations
    },
    'implementers': {
        'desc': 'State Wise Details (Phase 1)',
        'filename': 'implementers.csv',
        'scrape': get_implementers,
        'parse': parse_implementers
    },
    'panchayats': {
        'desc': 'Panchayat Ids',
        'filename': 'panchayats.csv',
        'scrape': get_panchayats,
        'parse': parse_panchayats
    },
    'planned_nofn': {
        'desc': 'Counts of GPs with hierarchy and implementers planned for NOFN Phase I',
        'filename': 'planned_nofn.csv',
        'scrape': get_planned_nofn,
        'parse': parse_planned_nofn
    }
}

def get_markdown_for_info(comp_info):
    full_str = ''
    filenames = comp_info['filename']
    if type(filenames) != list:
        filenames = [filenames]
    descs = comp_info['desc']
    if type(descs) != list:
        descs = [descs]

    if len(descs) != len(filenames):
        raise Exception('description count doesn\'t match filename count')
    location_steps = comp_info['bbnl_location']
    step_strs = []
    for i, step in enumerate(location_steps):
        padding = '  ' * (i + 1)
        if i == 0:
            padding = ''
        step_strs.append(padding + f'- {step}')
    location_str = '\n'.join(step_strs)
    for i, filename in enumerate(filenames):
        desc = descs[i]
        full_str += "---\n\n"
        full_str += f"## {filename}\n\n"
        full_str += f"description\n: {desc}\n\n"
        full_str += "Location in BBNL\n"
        full_str += f": {location_str}\n\n"
    return full_str


def get_last_updated_date(soup):
    bottom_div = soup.find('div', { 'id': "bottom" })
    visitor_panel = bottom_div.find('div', { 'class': 'visitor_panel' })
    updated_span = visitor_panel.find('span', { 'id': 'bottom_last' })
    last_updated_date_str = updated_span.text
    last_updated_date_str = last_updated_date_str.replace('Last Updated On:', '').strip()
    last_updated_date = datetime.strptime(last_updated_date_str, "%d/%m/%Y").date()
    return last_updated_date


def parse_main_page():
    logger.info('retrieving main page')
    url = 'http://www.bbnl.nic.in'
    web_data = requests.get(url)
    if not web_data.ok:
        raise Exception("unable to retrieve main page")
    soup = BeautifulSoup(web_data.text, 'html.parser')
    return soup


def is_leaf(node):
    parent = node.parent
    parent_name = parent.name 
    if parent_name != 'li':
        raise Exception(f'link expected to be in "li" but found under "{parent_name}"')

    for sibling in node.next_siblings:
        if sibling.name == 'ul':
            return False

    for sibling_of_parent in parent.next_siblings:
        if sibling_of_parent.name == 'ul':
            return False
    return True


def get_path(leaf):
    parents = list(leaf.parents)
    parents.reverse()
    parents.append(leaf)
    names_path = []
    logger.debug('{}'.format([x.name for x in parents]))
    for i, node in enumerate(parents):
        if node.name == 'ul':
            if parents[i+1].name == 'ul': 
                inter_node = node.contents[0].contents[0]
            else:
                inter_node = parents[i+1].contents[0]
            if inter_node.name != 'a':
                raise Exception(f'unexpected formating while walking for getting path.. expected "a" got {inter_node.name}') 
            names_path.append(inter_node.text)
    return names_path


def parse_sitemap():
    logger.info('retrieving sitemap page')
    sitemap_file = 'data/raw/sitemap.html'
    if not Path(sitemap_file).exists():
        url = 'http://www.bbnl.nic.in/sitemap.aspx'
        web_data = requests.get(url)
        if not web_data.ok:
            raise Exception("unable to retrieve sitemap page")
        html_text = web_data.text
        ensure_dir(sitemap_file)
        with open(sitemap_file, 'w') as f:
            f.write(html_text)
    else:
        logger.info('reading from local file')
        with open(sitemap_file, 'r') as f:
            html_text = f.read()

    soup = BeautifulSoup(html_text, 'html.parser')
    content_div = soup.find('div', {'id': 'cmscontent'})
    all_links = content_div.find_all('a')
    link_info_map = {}
    for link in all_links:
        if is_leaf(link):
            path = get_path(link)
            url = link.attrs['href']
            link_info_map[(*path,)] = url
    return link_info_map
            

def filter_sitemap(sitemap):
    new_map = {}
    for path, info in sitemap.items():
        curr = new_map
        for i, part in enumerate(path):
            if part not in curr:
                if i != len(path) - 1:
                    curr[part] = {}
                else:
                    curr[part] = 'ignore'
            curr = curr[part]

    with open('action_map.json', 'r') as f:
        old_map = json.load(f)

    diffs = diff(old_map, new_map, expand=True)
    interested = {}
    unknown = []
    for d in diffs:
        typ, path_dotted, values = d
        if typ == 'change':
            prev_value, curr_value = values
            path_parts = path_dotted.split('.')
            interested[(*path_parts,)] = { 'val': prev_value, 'url': sitemap[(*path_parts,)] }

        if typ == 'add':
            new_key = values[0][0]
            unknown.append(path_dotted + '.' + new_key)
    return interested, unknown





if __name__ == '__main__':
    import argparse

    all_comp_names = comp_map.keys()
    all_actions = ['list', 'scrape', 'parse']

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--comp', help=f'component to work on, should be one of {all_comp_names}', action='extend', nargs='+', type=str, default=[])
    parser.add_argument('-n', '--no-comp', help=f'component to skip, should be one of {all_comp_names}', action='extend', nargs='+', type=str, default=[])
    parser.add_argument('-a', '--action',  help=f'action to execute, one of {all_actions}', action='extend', nargs='+', type=str, default=[])
    parser.add_argument('-p', '--num-parallel', help='number of parallel processes to use', type=int, default=1)
    parser.add_argument('-l', '--log-level', help='Set the logging level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], type=str, default='DEBUG')
    args = parser.parse_args()

    setup_logging(args.log_level)

    actions_to_run = set(args.action)
    if len(actions_to_run) == 0:
        actions_to_run = set(all_actions)

    unknown_actions = actions_to_run - set(all_actions)
    if len(unknown_actions):
        raise Exception(f'unknown actions {unknown_actions} specified')

    soup = parse_main_page()
    last_updated_date = get_last_updated_date(soup)
    logger.info(f'last updated date on the site is {last_updated_date}')
    
    last_checked_date = None
    last_checked_date_filename = 'data/parsed/last_checked_date.txt'
    if Path(last_checked_date_filename).exists():
        with open(last_checked_date_filename, 'r') as f:
            content = f.read()
            last_checked_date = datetime.strptime(content, '%d-%m-%Y').date()
            logger.info(f'last checked date is {last_checked_date}')
    #if last_checked_date != None and last_checked_date > last_updated_date:
    #    logger.info('this site was checked after it was updated.. nothing new here')
    #    exit(0)
    
    sitemap = parse_sitemap()
    #logger.info(sitemap)
    interested, unknown = filter_sitemap(sitemap)
    for path in unknown:
        logger.warning(f'unknown path {path} found')
        #TODO: this should be an alert
        #TODO: write some file to disk and have github actions pick it up to create issue trackers

    comp_map_from_sitemap = {}
    for path, info in interested.items():
        value = info['val']
        url = info['url']
        logger.info(f'interested  path {path} -  {value} found')
        if value not in comp_map:
            continue
            #raise Exception(f'no entry for {value} in comp_map')
        comp_map[value]['url'] = url
        comp_map[value]['bbnl_location'] = path


    all_comp_names = set(all_comp_names)
    comps_to_run = set(args.comp)
    comps_to_not_run = set(args.no_comp)
    if len(comps_to_run) and len(comps_to_not_run):
        raise Exception("Can't specify bot comps to tun and not run")
    if len(comps_to_not_run) == 0:
        if len(comps_to_run) == 0:
            comps_to_run = all_comp_names
        unknown_comps = comps_to_run - all_comp_names
        if len(unknown_comps) != 0:
            raise Exception('Unknown components specified: {}'.format(unknown_comps))
    else:
        unknown_comps = comps_to_not_run - all_comp_names
        if len(unknown_comps) != 0:
            raise Exception('Unknown components specified: {}'.format(unknown_comps))
        comps_to_run = all_comp_names - comps_to_not_run

    with ProcessPoolExecutor(max_workers=args.num_parallel) as executor:
        for action in all_actions:
            if action not in actions_to_run:
                continue
            rets = []
            for comp in comps_to_run:
                comp_info = comp_map[comp]
                if action == 'list':
                    rets.append(get_markdown_for_info(comp_info))
                elif action == 'scrape':
                    func = comp_info['scrape']
                    func(executor, comp_info['url'])
                elif action == 'parse':
                    func = comp_info['parse']
                    func(executor)
            print('\n'.join(rets))

    with open(last_checked_date_filename, 'w') as f:
        date_str = datetime.now().strftime('%d-%m-%Y')
        f.write(date_str)
    logger.info(f'marking last checked date as {date_str}')
 

    

