import csv
import glob
import json
import logging

from operator import itemgetter
from pathlib import Path
from datetime import datetime
from concurrent.futures import (wait, ALL_COMPLETED,
                                Future, ThreadPoolExecutor)

import requests
from bs4 import BeautifulSoup

from common import is_problem_combo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

base_url = 'https://rfcoverage.dot.gov.in'
session = requests.session()

def request_args(self):
    return {
        'verify': not self.no_verify_ssl,
        'timeout': (self.connect_timeout, self.read_timeout)
    }



def get_date_str():
    date = datetime.today()
    date_str = date.strftime("%d%b%Y")
    return date_str


def get_states():
    logger.info('getting all states')
    web_data = session.get(base_url)
    if not web_data.ok:
        raise Exception(f'unable to retrieve {base_url}')
    soup = BeautifulSoup(web_data.text, 'html.parser')
    select = soup.find('select', { 'id': 'state'})
    options = select.find_all('option')
    state_infos = [ itemgetter(0,6)(x.attrs['value'].split('#')) for x in options if x.attrs['value'] != '' ]
    return state_infos


def get_districts(state_id):
    logger.info(f'getting districts for state {state_id}')
    url = f'{base_url}/ajax/getDistrict'
    headers = { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' }
    data = { 'id': f'{state_id}', 'type': 'state' }
    web_data = session.post(url, headers=headers, data=data)
    if not web_data.ok:
        raise Exception(f'unable to retrieve data from {url} for state {state_id}')
    data = json.loads(web_data.text)
    return data


def get_villages(dist_id):
    logger.info(f'getting villages for district {dist_id}')
    villages_filename = f'data/{get_date_str()}/villages.csv.{dist_id}'
    if Path(villages_filename).exists():
        logger.info(f'found {villages_filename}.. skip getting villages')
        village_infos = []
        with open(villages_filename, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                village_infos.append(r)
        return village_infos


    url = f'{base_url}/ajax/getVillage'
    headers = { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' }
    data = { 'id': f'{dist_id}', 'type': 'district' }
    web_data = session.post(url, headers=headers, data=data)
    if not web_data.ok:
        raise Exception(f'unable to retrieve data from {url} for dist {dist_id}')
    data = json.loads(web_data.text)
    Path(villages_filename).parent.mkdir(parents=True, exist_ok=True)
    logger.info(f'writing file {villages_filename}')
    with open(villages_filename, 'w') as f:
        if type(data) != list or len(data) == 0:
            logger.warning(f'got data: {data}')
            return []
        wr = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        wr.writeheader()
        for v in data:
            wr.writerow(v)
 
    return data


def get_all_districts(executor, state_infos):
    dists_filename = 'data/{get_date_str()}/districts.csv'
    dist_infos = []
    if Path(dists_filename).exists():
        logger.info(f'found {dists_filename}.. skip getting dists')
        with open(dists_filename, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                dist_infos.append(r)
        return dist_infos

    for s_id, s_name in state_infos:
        data = get_districts(s_id)
        for rec in data:
            rec['state_name'] = s_name
        dist_infos.extend(data)

    logger.info('writing file: {dists_filename}')
    Path(dists_filename).parent.mkdir(parents=True, exist_ok=True)
    with open(dists_filename, 'w') as f:
        if len(dist_infos) == 0:
            return dist_infos
        wr = csv.DictWriter(f, fieldnames=list(dist_infos[0].keys()))
        wr.writeheader()
        for d in dist_infos:
            wr.writerow(d)

    return dist_infos


known_problem_districts = ['1002']

def get_hierarchy_data(executor, state_infos):
    hierarchy_filename = 'data/{get_date_str()}/villages.csv'
    if Path(hierarchy_filename).exists():
        logger.info(f'found {hierarchy_filename}.. skip getting hierarchy')
        return hierarchy_filename

    district_infos = get_all_districts(executor, state_infos)
    village_infos = []
    failed_ids = []
    for d in district_infos:
        if str(d['id']) in known_problem_districts: 
            logger.warning(f"ignoring known problematic district id: {d['id']}")
            continue
        try:
            data = get_villages(d['id'])
        except:
            logger.exception(f"unable to get data for district: {d['id']}")
            failed_ids.append(d['id'])
            continue

        for v in data:
            v['state_id'] = d['state_id']
            v['state_name'] = d['state_name']
            v['district_name'] = d['name']
            village_infos.append(v)

    logger.info(f'{ failed_ids = }')
    with open(f'data/{get_date_str()}/hierarchy_failed_states.txt', 'w') as f:
        for idx in failed_ids:
            f.write(f'{idx}\n')
    logger.info(f'writing file: {hierarchy_filename}')
    Path(hierarchy_filename).parent.mkdir(parents=True, exist_ok=True)
    with open(hierarchy_filename, 'w') as f:
        wr = csv.DictWriter(f, fieldnames=(village_infos[0].keys()))
        wr.writeheader()
        for v in village_infos:
            wr.writerow(v)

    to_delete = glob.glob(f'data/{get_date_str()}/villages.csv.*')
    to_delete += [ 'data/{get_date_str()}/districts.csv' ]
    logger.info(f'deleting files: {to_delete}')
    [ Path(fname).unlink() for fname in to_delete ]

    return hierarchy_filename


def get_state_network_data(tsp, technology):
    logger.info(f'getting network info for {tsp}, {technology}')
    network_data_filename =f'data/{get_date_str()}/network_data.csv.{tsp}.{technology}'
    if Path(network_data_filename).exists():
        logger.info(f'found {network_data_filename}.. skip getting network data')
        nw_infos = []
        with open(network_data_filename, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                nw_infos.append(r)
        return nw_infos


    url = f'{base_url}/ajax/getNetworkData'
    headers = { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' }
    data = { 'id': '1',
             'type': 'network_data',
             'fetchData': 'village',
             'tsp[]': tsp,
             'technology[]': technology }
    web_data = session.post(url, headers=headers, data=data)
    if not web_data.ok:
        raise Exception(f'unable to retrieve village data from {url=} for {data=}, status:{web_data.status_code}')

    if web_data.text == 'not_found':
        data = []
    else:
        data = json.loads(web_data.text)
    Path(network_data_filename).parent.mkdir(parents=True, exist_ok=True)
    logger.info(f'writing file {network_data_filename}')
    with open(network_data_filename, 'w') as f:
        if type(data) != list or len(data) == 0:
            logger.warning(f'got data: {data}')
            return []
        wr = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        wr.writeheader()
        for v in data:
            wr.writerow(v)
    return data


def get_network_data(executor):
    date_str = get_date_str()
    network_data_filename =f'data/{date_str}/network_data.csv'
    if Path(network_data_filename).exists():
        logger.info(f'found {network_data_filename}.. skip getting network data')
        nw_infos = []
        with open(network_data_filename, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                nw_infos.append(r)
        return nw_infos

    tsps = [ 'AIRTEL', 'BSNL', 'MTNL', 'JIO', 'Vi India']
    technologies = ['2G', '3G', '4G']
    nw_infos = []
    fut_map = {}
    for tsp in tsps:
        for technology in technologies:
            if is_problem_combo(tsp, technology):
                continue
            fut = executor.submit(get_state_network_data, tsp, technology)
            fut_map[fut] = (tsp, technology)

    has_errors = False
    done, not_done = wait(fut_map, return_when=ALL_COMPLETED)
    for fut in done:
        tsp, technology = fut_map[fut]
        try:
            data = fut.result()
        except:
            logger.exception(f'network data extraction for {tsp} {technology} failed')
            has_errors = True
            continue
        for rec in data:
            rec = {k:v.replace('\n', '').strip() for k,v in rec.items()}
            nw_infos.append(rec)
    if has_errors:
        logger.error('Found errors while extracting network map')
        raise Exception('Some tasks failed')

    rec_set = set()
    for r in nw_infos:
        val = tuple(r.values())
        if val in rec_set:
            continue
        rec_set.add(val)

    header = list(nw_infos[0].keys()) + ['scrape_date']
    Path(network_data_filename).parent.mkdir(parents=True, exist_ok=True)
    logger.info(f'writing file {network_data_filename}')
    with open(network_data_filename, 'w') as f:
        wr = csv.writer(f)
        wr.writerow(header)
        for r in rec_set:
            wr.writerow(list(r) + [date_str])

    to_delete = glob.glob(f'data/{get_date_str()}/network_data.csv.*')
    logger.info(f'deleting files: {to_delete}')
    [ Path(fname).unlink() for fname in to_delete ]
    return network_data_filename


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--parallel', help='number of parallel downloads', type=int, default=1)
    parser.add_argument('-c', '--comp', help='which component to download', choices=['villages', 'network'], default='network')
    args = parser.parse_args()

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        state_infos = get_states()
        if args.comp == 'villages':
            filename = get_hierarchy_data(executor, state_infos)
        elif args.comp == 'network':
            filename = get_network_data(executor)



