# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "bs4",
#     "colorlog",
#     "imgcat",
#     "numpy",
#     "opencv-python-headless",
#     "pillow",
#     "pushbullet-py",
#     "pytesseract",
#     "requests",
#     "websocket-client",
# ]
# ///

import os
import logging
import shutil
import time

from pathlib import Path

#import requests

from bs4 import BeautifulSoup

from captcha_helper import (
     check_captcha_models,
     CAPTCHA_MANUAL,
     captcha_model_dir
)
from login import login_wrap, get_form_data, get_secrets
from common import (
    base_url,
    setup_logging,
    get_page_soup,
    session
)


logger = logging.getLogger(__name__)

data_dir = 'data/'
raw_data_dir = data_dir + 'raw/villages/'
MAX_CAPTCHA_ATTEMPTS = 10
DELAY = 1
DELAY_DOWNLOAD = 1
FORCE = (os.environ.get('FORCE', '0') == '1')
FORCE_UNAVAILABLE = (os.environ.get('FORCE_UNAVAILABLE', '0') == '1')


def check_for_error(resp, err_file=None):
    global force_map_tried
    resps = list(resp.history) + [resp]
    for r in resps:
        if '/Errorpage.aspx' in str(r.url):
            soup = BeautifulSoup(resp.text, 'html.parser')
            main_div = soup.find('div', { 'id': 'divMain'})
            err_div = main_div.find('div', { 'class': 'errorHeading'})
            err_text = err_div.text
            err_strings = [ 'Ooops! Something went wrong.',
                            'We apologize for the inconvenience. Please try again later.']
            for e in err_strings:
                if e in err_text:
                    if err_file is not None:
                        d_file = err_file.parent
                        s_file = d_file.parent
                        s_name = s_file.name
                        d_name = d_file.name
                        if s_name not in force_map_tried:
                            force_map_tried[s_name] = {}
                        force_map_tried[s_name][d_name] = True

                        err_file.write_text(resp.text)
                    raise Exception('Retriable Exception')
            raise Exception('Some Error Happened')

def scrape(phone_num, password, otp_from_pb):
    global done_states
    global force_map_tried
    login_wrap(phone_num, password, otp_from_pb)
    logging.info('Product Show page scraping')
    dp_page = base_url + 'Digital_Product_Show.aspx'
    soup = get_page_soup(dp_page)
    form_data = get_form_data(soup)
    post_data = {
        'ctl00$ContentPlaceHolder1$rblDigitalProduct': '7',
        'ctl00$ContentPlaceHolder1$rblFormats': 'SHAPEFILE'
    }
    form_data.update(post_data)
    headers = {
        "origin": base_url[:-1],
        "referer": dp_page,
        "content-type": "application/x-www-form-urlencoded",
    }
    resp = session.post(dp_page, headers=headers, data=form_data)
    if not resp.ok:
        raise Exception('Unable to post to get village shapefile listing')
    check_for_error(resp)
    soup = BeautifulSoup(resp.text, 'html.parser')
    main_div = soup.find('div', { 'id': 'divMain' })
    a_s = main_div.find_all('a')
    val = None
    for a in a_s:
        if a.text.strip() != 'Click to Buy':
            continue
        href = a.attrs['href']
        val = href.split("'")[1]

    if val is None:
        raise Exception("couldn't find product link")
    form_data = get_form_data(soup)
    form_data['__EVENTTARGET'] = val
    resp = session.post(dp_page, headers=headers, data=form_data)
    if not resp.ok:
        raise Exception('Unable to post to get village shapefile page')
    check_for_error(resp)
    soup = BeautifulSoup(resp.text, 'html.parser')
    sel = soup.find('select')
    sel_id = sel.attrs['id']
    form_data = get_form_data(soup)
    options = sel.find_all('option')
    state_map = {}
    for o in options:
        s_id = o.attrs['value']
        if s_id == "0":
            continue
        s_name = o.text
        state_map[s_name] = s_id
    logging.info(state_map)
    ps_page = base_url + 'Product_Specification.aspx'
    for s_name, s_id in state_map.items():
        if s_name in done_states:
            continue
        logging.info(f'handling state {s_name}')
        state_dir = raw_data_dir + s_name
        state_dir_path = Path(state_dir)
        state_dir_path.mkdir(exist_ok=True, parents=True)
        logging.info('getting dist list')
        s_form_data = {}
        s_form_data.update(form_data)
        s_form_data.update({
            'ctl00$ContentPlaceHolder1$ddlDemographicState': state_map[s_name],
            'ctl00$ContentPlaceHolder1$ddlDemographicDistrict': '0',
            'ctl00$ContentPlaceHolder1$ddlstate': '0',
            'ctl00$ContentPlaceHolder1$ddldist': '0'
        })
        s_form_data['__EVENTTARGET'] = sel_id
        headers['referer'] = ps_page
        time.sleep(DELAY)
        resp = session.post(ps_page, headers=headers, data=s_form_data)
        if not resp.ok:
            raise Exception('Unable to post to get dist list')
        check_for_error(resp)
        soup = BeautifulSoup(resp.text, 'html.parser')
        form_data = get_form_data(soup)
        sels = soup.find_all('select')

        sel_d_id = sels[1].attrs['id']
        options = sels[1].find_all('option')
        for o in options:
            d_id = o.attrs['value']
            if d_id == "0":
                continue
            d_name = o.text
            logging.info(f'handling district {d_name}')
            dist_dir_path = state_dir_path / d_name
            dist_dir_path.mkdir(exist_ok=True, parents=True)
            data_file = dist_dir_path / 'data.zip'
            err_file = dist_dir_path / 'err.txt'
            if data_file.exists():
                logging.warning(f'{data_file} already exists.. skipping')
                continue
            if err_file.exists():
                logging.warning(f'{err_file} already exists.. skipping')
                if not FORCE:
                    continue

                if err_file.read_text().strip() == 'Not Available' and not FORCE_UNAVAILABLE:
                    continue
                f_d_map = force_map_tried.get(s_name, {})
                if d_name in f_d_map:
                    continue
                err_file.unlink()
                logging.info('FORCE mode.. retry errors')
            logging.info('getting dist link')
            d_form_data = {} 
            d_form_data.update(form_data)
            d_form_data.update({
                'ctl00$ContentPlaceHolder1$ddlDemographicState': s_id,
                'ctl00$ContentPlaceHolder1$ddlDemographicDistrict': d_id,
                'ctl00$ContentPlaceHolder1$ddlstate': '0',
                'ctl00$ContentPlaceHolder1$ddldist': '0',
            })
            d_form_data['__EVENTTARGET'] = sel_d_id
            time.sleep(DELAY)
            resp = session.post(ps_page, headers=headers, data=d_form_data)
            if not resp.ok:
                raise Exception('Unable to post to get dist link')
            check_for_error(resp, err_file)
            form_data = get_form_data(soup)
            logging.info('add to cart page')
            d_c_form_data = {}
            d_c_form_data.update(form_data)
            d_c_form_data.update({
                'ctl00$ContentPlaceHolder1$ddlDemographicState': s_id,
                'ctl00$ContentPlaceHolder1$ddlDemographicDistrict': d_id,
                'ctl00$ContentPlaceHolder1$ddlstate': '0',
                'ctl00$ContentPlaceHolder1$ddldist': '0',
            })
            d_c_form_data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$lbtnAddToCart'
       
            time.sleep(DELAY)
            resp = session.post(ps_page, headers=headers, data=d_c_form_data)
            if not resp.ok:
                raise Exception('Unable to add to cart')
            check_for_error(resp, err_file)
            soup = BeautifulSoup(resp.text, 'html.parser')
            msg_el = soup.find('span', { 'id': "ContentPlaceHolder1_lblMsgLeyarSelection" })
            logger.debug(f'{msg_el}')
            if msg_el is not None and \
               msg_el.text.strip() == "Selected Product currently not available kindly contact Survey of India":
                   logger.warning('District Unavailable')
                   err_file.write_text('Not Available')
                   continue
            form_data = get_form_data(soup)
            logging.info('show cart page')
            d_s_form_data = {}
            d_s_form_data.update(form_data)
            d_s_form_data.update({
                'ctl00$ContentPlaceHolder1$ddlDemographicState': s_id,
                'ctl00$ContentPlaceHolder1$ddlDemographicDistrict': d_id,
                'ctl00$ContentPlaceHolder1$ddlstate': '0',
                'ctl00$ContentPlaceHolder1$ddldist': '0',
                'ctl00$ContentPlaceHolder1$btnViewCart': 'View Cart'
            })
            time.sleep(DELAY)
            resp = session.post(ps_page, headers=headers, data=d_s_form_data)
            if not resp.ok:
                raise Exception('Unable to show cart')
            check_for_error(resp, err_file)
            soup = BeautifulSoup(resp.text, 'html.parser')
            form_data = get_form_data(soup)
            logging.info('Placing order')
            ac_page = base_url + 'addtocart.aspx'
            d_ac_form_data = {}
            d_ac_form_data.update(form_data)
            d_ac_form_data.update({
                'ctl00$ContentPlaceHolder1$btnplaceorder': 'Place Order',
                'ctl00$ContentPlaceHolder1$HiddenField1': ''
            })
            headers['referer'] = ac_page
            resp = session.post(ac_page, headers=headers, data=d_ac_form_data)
            if not resp.ok:
                raise Exception('Unable to place order')
            check_for_error(resp, err_file)
            soup = BeautifulSoup(resp.text, 'html.parser')
            form_data = get_form_data(soup)

            logging.info('Agree to terms')
            d_ag_form_data = {}
            d_ag_form_data.update(form_data)
            d_ag_form_data.update({
                'ctl00$ContentPlaceHolder1$btnSubmitPrivateIndenter': 'I Agree',
                'ctl00$ContentPlaceHolder1$HiddenField1': ''
            })
            headers['referer'] = ac_page
            resp = session.post(ac_page, headers=headers, data=d_ag_form_data)
            if not resp.ok:
                raise Exception('Unable to agree to terms')
            check_for_error(resp, err_file)

            soup = BeautifulSoup(resp.text, 'html.parser')
            form_data = get_form_data(soup)

            logging.info('Proceed to Download')
            uod_page = base_url + 'UserOrderDetails.aspx'
            headers['referer'] = uod_page
            d_rd_form_data = {}
            d_rd_form_data.update(form_data)
            d_rd_form_data['ctl00$ContentPlaceHolder1$gvCustomers$ctl02$btnProceedDownload'] = 'Proceed for Download'
            time.sleep(DELAY)
            resp = session.post(uod_page, headers=headers, data=d_rd_form_data)
            if not resp.ok:
                raise Exception('Unable to do something')
            check_for_error(resp, err_file)

            logging.info('Request Download')
            soup = BeautifulSoup(resp.text, 'html.parser')
            form_data = get_form_data(soup)
            uor_page = base_url + 'UserOrderRequest.aspx'
            d_od_form_data = {}
            d_od_form_data.update(form_data)
            d_od_form_data.update({
                'ctl00$ContentPlaceHolder1$gvOrders$ctl02$btnRequest': 'Request'
            })
            headers['referer'] = uor_page
            time.sleep(DELAY)
            resp = session.post(uor_page, headers=headers, data=d_od_form_data)
            if not resp.ok:
                raise Exception('Unable to create generate download link')
            check_for_error(resp, err_file)
            soup = BeautifulSoup(resp.text, 'html.parser')
            form_data = get_form_data(soup)


            logging.info('generate Download link')
            d_gdl_form_data = {}
            d_gdl_form_data.update(form_data)
            d_gdl_form_data.update({
                'ctl00$ContentPlaceHolder1$gvOrders$ctl02$btnGenerateDownloadLink': 'Generate Download Link'
            })
            time.sleep(DELAY)
            resp = session.post(uor_page, headers=headers, data=d_gdl_form_data)
            if not resp.ok:
                raise Exception('Unable to create download map link')
            check_for_error(resp, err_file)

            logging.info('Download map')
            soup = BeautifulSoup(resp.text, 'html.parser')
            form_data = get_form_data(soup)
            d_f_form_data = {}
            d_f_form_data.update(form_data)
            d_f_form_data.update({
                'ctl00$ContentPlaceHolder1$gvOrders$ctl02$btnDownloadMap': 'Download'
            })
            time.sleep(DELAY_DOWNLOAD)
            resp = session.post(uor_page, headers=headers, data=d_f_form_data)
            if not resp.ok:
                raise Exception('Unable to download map')
            check_for_error(resp, err_file)
            with open(data_file, 'wb') as f:
                f.write(resp.content)
            return False
        done_states.append(s_name)
    return True



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

 
def scrape_wrap(otp_from_pb):
    secrets_map = get_secrets()
    tried_users = get_tried_users()
    secrets_map = {k:v for k,v in secrets_map.items() if k not in tried_users}
    total_count = len(secrets_map)
    s_items = list(secrets_map.items())
    p_idx = 0
    while True:
        if p_idx >= total_count:
            logger.warning('No more users!!')
            break
        phone_num, password = s_items[p_idx]
        try:
            logger.info(f'scraping with phone number: {p_idx + 1}/{total_count}')
            ret = scrape(phone_num, password, otp_from_pb)
            if ret:
                if Path(tried_users_file).exists():
                    Path(tried_users_file).unlink()
                break
            else:
                continue
        except Exception as ex:
            if str(ex) != 'Retriable Exception':
                raise
            logger.warning('Retriable Exception for this user.. changing users')
            p_idx += 1
            #tried_users.append(phone_num)
            #update_tried_users(tried_users)
            #session = requests.session()
    if Path(tried_users_file).exists():
        Path(tried_users_file).unlink()


if __name__ == '__main__':
    setup_logging(logging.INFO)

    if not CAPTCHA_MANUAL:
        check_captcha_models(captcha_model_dir)


    done_states = []
    force_map_tried = {}
    otp_from_pb = True
    scrape_wrap(otp_from_pb)

