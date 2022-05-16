import os
import glob
import json
import pickle
import logging
import shutil
import zipfile

from pprint import pformat
from pathlib import Path
from datetime import datetime
from functools import cmp_to_key

#import requests

from bs4 import BeautifulSoup

from captcha_helper import (
     get_captcha_from_page,
     prepare_captcha_models,
     CAPTCHA_MANUAL,
     captcha_model_dir
)
from login import login, get_form_data
from common import (
    base_url,
    setup_logging,
    ensure_dir,
    session
)


logger = logging.getLogger(__name__)

data_dir = 'data/'
raw_data_dir = data_dir + 'raw/'
MAX_CAPTCHA_ATTEMPTS = 6


def get_secrets():
    with open(data_dir + 'users.json', 'r') as f:
        users_text = f.read()
    users_data = json.loads(users_text)

    with open(data_dir + 'users_extra.json', 'r') as f:
        users_text = f.read()
    users_data.extend(json.loads(users_text))

    secrets_map = {
        u['phone_num']:u['password']
        for u in users_data
        if not u['first_login']
    }
    return secrets_map

tried_users_file = data_dir + 'tried_users.txt'
def get_tried_users():
    if not Path(tried_users_file).exists():
        return []
    with open(tried_users_file, 'r') as f:
        tried_users = f.read().split('\n')
    return [ x.strip() for x in tried_users ]


def update_tried_users(tried_users):
    tried_users_file_new = tried_users_file + '.new'
    with open(tried_users_file_new, 'w') as f:
        f.write('\n'.join(tried_users))
    shutil.move(tried_users_file_new, tried_users_file)
    

def login_wrap(phone_num, password):
    global session
    FAILED_CAPTCHA = 'Please enter valid Captcha'
    saved_cookie_file = f'data/cookies/saved_cookies.{phone_num}.pkl'
    if Path(saved_cookie_file).exists():
        logger.info('found saved cookie file')
        with open(saved_cookie_file, 'rb') as f:
            saved_cookies = pickle.load(f)
        cookies_valid = True
        current_time = datetime.now()

        for cookie in saved_cookies:
            if cookie.expires is not None:
                expiry_time = datetime.fromtimestamp(cookie.expires)
                logging.info(f'cookie expiry time: {expiry_time}')
                logging.info(f'current time: {datetime.now()}')
                if expiry_time < current_time:
                    logger.warning(f'{cookie.name} expired')
                    cookies_valid = False
                    break

        if cookies_valid:
            session.cookies.update(saved_cookies)
            logger.info('logged in with saved cookie')
            return
        Path(saved_cookie_file).unlink()
        logger.warning('deleting old cookie file')

    count = 0
    success = False
    while count < MAX_CAPTCHA_ATTEMPTS:
        try:
            logger.info('attempting a login')
            login(phone_num, password)
            ensure_dir(saved_cookie_file)
            logger.info('saving cookies to file')
            with open(saved_cookie_file, 'wb') as f:
                pickle.dump(session.cookies, f)
            success = True
            logger.info('logged in')
            break
        except Exception as ex:
            if str(ex) != FAILED_CAPTCHA:
                raise ex
            logger.warning('captcha failed..')
            count += 1

    if not success:
        raise Exception('login failed because of captcha errors')

            
def get_map_index_form_data(soup):
    form_data = {}
    form_data['ctl00$ContentPlaceHolder1$rblFreeProduct'] = '1'
    form_data['ctl00$ContentPlaceHolder1$gvFreeProduct$ctl02$btnDownloadMap'] = 'Click to Download'
    return form_data


def download_index_file():
    out_file = raw_data_dir + 'OSM_SHEET_INDEX.zip'
    if Path(out_file).exists():
        logging.info(f'{out_file} exists.. skipping')
        return out_file
    url = base_url + 'FreeOtherMaps.aspx'
    resp = session.get(url)
    if not resp.ok:
        raise Exception('unable to get FreeOtherMaps page')
    soup = BeautifulSoup(resp.text, 'html.parser')
    form_data = get_form_data(soup)
    form_data.update(get_map_index_form_data(soup))
    logger.debug(f'index file form data:\n{pformat(form_data)}')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    resp = session.post(url, data=form_data, headers=headers)
    logger.debug(f'status_code = {resp.status_code} headers:\n{pformat(dict(resp.headers))}')
    if not resp.ok:
        raise Exception('FreeOtherMaps failed')
    ensure_dir(out_file)
    logger.info(f'writing file {out_file}')
    with open(out_file, 'wb') as f:
        f.write(resp.content)
    return out_file


def unzip_file(zip_filename):
    target_dir = Path(zip_filename).parent
    logger.info(f'unzipping {zip_filename} to {target_dir}')
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(target_dir)

    extracted_dir = zip_filename.replace('.zip', '/')
    return extracted_dir


def adjust_coordinates(f):
    coords = f['geometry']['coordinates'][0][:-1]
    coords = [ [round(c[0], 2), round(c[1], 2)] for c in coords ]
    indices = range(0,4)
    def cmp(ci1, ci2):
        c1 = coords[ci1]
        c2 = coords[ci2]
        if c1[0] == c2[0]:
            return c1[1] - c2[1]
        else:
            return c1[0] - c2[0]

    #print(f'{coords=}')
    s_indices = sorted(indices, key=cmp_to_key(cmp))
    #print(s_indices)
    lb = s_indices[0]
    lt = (lb + 1) % 4
    rt = (lb + 2) % 4
    rb = (lb + 3) % 4
    out_coords = [ coords[lt], coords[lb], coords[rb], coords[rt], coords[lt] ]
    #print(f'{out_coords=}')
    f['geometry']['coordinates'] = [ out_coords ]



def correct_index_file(out_filename):
    with open(out_filename, 'r') as f:
        index_data = json.load(f)

    corrections_file = Path(__file__).parent.joinpath('index.geojson.corrections')
    with open(corrections_file, 'r') as f:
        index_corrections_data = json.load(f)

    corrections_map = {f['properties']['EVEREST_SH']:f for f in index_corrections_data['features']}

    for f in index_data['features']:
        sheet_no = f['properties']['EVEREST_SH']
        if sheet_no not in corrections_map:
            continue
        geom_correction = corrections_map[sheet_no]['geometry']
        f['geometry'] = geom_correction

    for f in index_data['features']:
        adjust_coordinates(f)

    out_filename_new = out_filename + '.new'
    with open(out_filename_new, 'w') as f:
        json.dump(index_data, f, indent=4)
    shutil.move(out_filename_new, out_filename)


def convert_shp_to_geojson(unzipped_folder, out_filename):
    filenames = glob.glob(str(Path(unzipped_folder).joinpath('*.shp')))
    assert len(filenames) == 1, f'{list(filenames)}'
    shp_file = filenames[0]
    os.system(f'ogr2ogr -f GeoJSON -t_srs EPSG:4326 {out_filename} {shp_file}')
    correct_index_file(out_filename)


def get_map_index():
    filename = data_dir + 'index.geojson'

    logger.info('getting map index')
    if Path(filename).exists():
        logger.info(f'{filename} exists.. skipping')
        return filename

    raw_filename = download_index_file()
    unzipped_folder = unzip_file(raw_filename)
    convert_shp_to_geojson(unzipped_folder, filename)
    shutil.rmtree(unzipped_folder)
    return filename


def get_tile_infos(map_index_file):
    with open(map_index_file, 'r') as f:
        map_data = json.load(f)
    features = map_data['features']
    return [ x['properties'] for x in features ]


def get_download_tile_form_data(soup, sheet_no, first_pass=True):
    captcha = ''
    form_data = {}
    form_data['ctl00$ContentPlaceHolder1$ddlstate'] = '0'
    form_data['ctl00$ContentPlaceHolder1$ddldist'] = '0'
    form_data['ctl00$ContentPlaceHolder1$txtSheetNumber'] = sheet_no
    form_data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$lbtnDownloadMap'

    if not first_pass:
        captcha = get_captcha_from_page(soup)
        form_data['ctl00$ContentPlaceHolder1$CheckBox1'] = 'on'
        form_data['ctl00$ContentPlaceHolder1$Button_ok'] = 'OK'
        form_data['__EVENTTARGET'] = ''

    form_data['ctl00$ContentPlaceHolder1$txtCaptchaMtr'] = captcha
    return form_data


def download_tile(sheet_no):

    out_filename = Path(raw_data_dir).joinpath(f"{sheet_no.replace('/', '_')}.pdf")
    out_filename_unavailable = Path(str(out_filename) + '.unavailable')
    file_to_write = out_filename
    if out_filename.exists() or out_filename_unavailable.exists():
        logger.info(f'{out_filename} exists.. skipping')
        return

    url = base_url + 'FreeMapSpecification.aspx'
    resp = session.get(url)
    if not resp.ok:
        raise Exception('unable to get FreeMapSpec page')
    soup = BeautifulSoup(resp.text, 'html.parser')


    form_data = get_form_data(soup)
    form_data.update(get_download_tile_form_data(soup, sheet_no, first_pass=True))
    logger.debug(f'spec page form data first pass:\n{pformat(form_data)}')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    resp = session.post(url, data=form_data, headers=headers)
    logger.debug(f'status_code = {resp.status_code} headers:\n{pformat(dict(resp.headers))}')
    if not resp.ok:
        raise Exception('unable to lookup {sheet_no} in FreeMapSpec page')
    soup = BeautifulSoup(resp.text, 'html.parser')


    form_data = get_form_data(soup)
    form_data.update(get_download_tile_form_data(soup, sheet_no, first_pass=False))
    logger.debug(f'spec page form data second pass:\n{pformat(form_data)}')
    resp = session.post(url, data=form_data, headers=headers)
    logger.debug(f'status_code = {resp.status_code} headers:\n{pformat(dict(resp.headers))}')
    if not resp.ok:
        raise Exception('unable to download {sheet_no=}')

    if resp.headers['Content-Type'] != 'text/html; charset=utf-8':
        content = resp.content
    else:
        soup = BeautifulSoup(resp.text, 'html.parser')

        captcha_failed = soup.find('span', { 'id': 'ContentPlaceHolder1_lblWrongCaptcha'})
        CAPTCHA_FAILED_MSG = 'Please enter valid captcha code'
        if captcha_failed is not None and captcha_failed.text == CAPTCHA_FAILED_MSG:
            raise Exception('Captcha Failed')

        limit_crossed = soup.find('span', { 'id': 'ContentPlaceHolder1_msgbox_lblMsg'})
        LIMIT_CROSSED_MSG = 'You have crossed your download limit for today'
        if limit_crossed is not None and limit_crossed.text == LIMIT_CROSSED_MSG:
            raise Exception('Limit Crossed')

        error_heading = soup.find('div', {'class': 'errorHeading'})
        if error_heading is not None:
            raise Exception(f'Unexpected Error: {error_heading.text}')

        not_found = soup.find('span', {'id':'ContentPlaceHolder1_lblSheetNotExist'})
        NOT_FOUND_MSG = 'Sheet is not available. Please contact to Survey of India.'
        if not_found is not None and not_found.text == NOT_FOUND_MSG:
            logger.warning('sheet not found, writing unavailable file')
            file_to_write = out_filename_unavailable
            content = b''
        else:
            with open('failed.html', 'w') as f:
                f.write(resp.text)
            logger.error(f'status_code = {resp.status_code} headers:\n{pformat(dict(resp.headers))}')
            logger.error(resp.text)
            raise Exception(f'Expected pdf got html for {sheet_no}')


    #TODO check if returned content is pdf or html?
    ensure_dir(file_to_write)
    logger.info(f'writing file {file_to_write}')
    with open(file_to_write, 'wb') as f:
        f.write(content)
    return out_filename



def download_tile_wrap(tile_info):
    count = 0
    success = False
    sheet_no = tile_info['EVEREST_SH']
    logger.info(f'downloading {sheet_no=}')
    while count < MAX_CAPTCHA_ATTEMPTS:
        try:
            download_tile(sheet_no)
            success = True
            break
        except Exception as ex:
            if str(ex) != 'Captcha Failed':
                raise ex
            count += 1
            logger.warning('captcha failed..')

    if not success:
        raise Exception('download tile map because of captcha errors')


def get_done_list():
    filename = data_dir + 'files_done.txt'
    if not Path(filename).exists():
        return []
    with open(filename, 'r') as f:
        files_done = f.read().split('\n')
    return [ x.strip() for x in files_done ]

def get_priority_list():
    filename = data_dir + 'priority_list.txt'
    if not Path(filename).exists():
        return []

    with open(filename, 'r') as f:
        plist = f.read().split('\n')
    plist = [ x.strip() for x in plist ]
    plist = [ x for x in plist if x != '' ]
    return plist


def is_sheet_done(sheet_no, done, only_unavailable):
    base_file = f"{sheet_no.replace('/', '_')}.pdf"
    base_file_unavailable = base_file + '.unavailable'
    out_filename = Path(raw_data_dir).joinpath(base_file)
    out_filename_unavailable = Path(raw_data_dir).joinpath(base_file_unavailable)
    if out_filename.exists() or \
       out_filename_unavailable.exists() or \
       base_file in done or \
       ( not only_unavailable and base_file_unavailable in done ):
           return True
    return False


def scrape(phone_num, password, only_unavailable):
    login_wrap(phone_num, password)
    map_index_file = get_map_index()

    tile_infos = get_tile_infos(map_index_file)
    logger.info(f'got {len(tile_infos)} tiles')


    priority_list = get_priority_list()
    priority_tile_info_map = {}
    done = get_done_list()
    tile_infos_to_download = []
    for tile_info in tile_infos:
        sheet_no = tile_info['EVEREST_SH']
        if is_sheet_done(sheet_no, done, only_unavailable):
            continue
        if sheet_no in priority_list:
            priority_tile_info_map[sheet_no] = tile_info
        else:
            tile_infos_to_download.append(tile_info)

    for sheet_no in priority_list:
        if sheet_no not in priority_tile_info_map:
            if not is_sheet_done(sheet_no, done, only_unavailable):
                logger.warning(f'priority {sheet_no} missing')
            continue
        tile_info = priority_tile_info_map[sheet_no]
        download_tile_wrap(tile_info)

    for tile_info in tile_infos_to_download:
        download_tile_wrap(tile_info)


def scrape_wrap(only_unavailable):
    global session
    secrets_map = get_secrets()
    p_idx = 0
    tried_users = get_tried_users()
    secrets_map = {k:v for k,v in secrets_map.items() if k not in tried_users}
    total_count = len(secrets_map)
    for phone_num, password in secrets_map.items():
        p_idx += 1
        try:
            logger.info(f'scraping with phone number: {p_idx}/{total_count}')
            scrape(phone_num, password, only_unavailable)
        except Exception as ex:
            if str(ex) != 'Limit Crossed':
                raise
            logger.warning('Limit crossed for this user.. changing users')
            tried_users.append(phone_num)
            update_tried_users(tried_users)
            #session = requests.session()
    logger.warning('No more users')
    if Path(tried_users_file).exists():
        Path(tried_users_file).unlink()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--max-captcha-retries', help='max number of times a captcha is retried', type=int, default=MAX_CAPTCHA_ATTEMPTS)
    parser.add_argument('-u', '--unavailable', help='try getting the unavailable files', action='store_true')
    args = parser.parse_args()
    MAX_CAPTCHA_ATTEMPTS = args.max_captcha_retries

    setup_logging(logging.INFO)

    if not CAPTCHA_MANUAL:
        prepare_captcha_models(captcha_model_dir)

    scrape_wrap(args.unavailable)




    
