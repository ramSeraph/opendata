import re
import hashlib
import logging

import json
import pickle
from pprint import pformat
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from captcha_helper import get_captcha_from_page
from common import base_url, get_form_data, session, ensure_dir, data_dir

from otp import setup_otp_listener, get_otp_pb, get_otp_manual

logger = logging.getLogger(__name__)

MAX_CAPTCHA_ATTEMPTS = 20

def get_secrets():
    with open(data_dir + 'users.json', 'r') as f:
        users_text = f.read()
    users_data = json.loads(users_text)

    secrets_map = {
        u['phone_num']:u['password']
        for u in users_data
        if not u['first_login']
    }
    return secrets_map

def get_salt(soup):
    div = soup.find('div', {'id': 'divMain'})
    a = div.find('a', { 'id': 'ContentPlaceHolder1_btnLoginMTR' })
    
    onclick_text = a.attrs.get('onclick')
    m = re.match(r"^return HashPasswordwithSaltMTR\('(.*)'\);", onclick_text)
    if m is None:
        raise Exception('onclick text not as expected')
    salt = m.group(1)
    logger.info(f'{salt=}')
    return salt


def prepare_password(password, salt):
    password = hashlib.sha256(password.encode('utf8')).hexdigest()
    password += salt
    password = hashlib.sha256(password.encode('utf8')).hexdigest()
    return password


def get_login_form_data(soup, phone_num, password):
    salt = get_salt(soup)
    password = prepare_password(password, salt)
    captcha = get_captcha_from_page(soup)
    form_data = {}
    form_data['ctl00$ContentPlaceHolder1$txtMtrMobileNo'] = phone_num
    form_data['ctl00$ContentPlaceHolder1$txtMtrPassword'] = password
    form_data['ctl00$ContentPlaceHolder1$txtCaptchaMtr'] = captcha
    form_data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$btnLoginMTR'
    return form_data

def get_login_otp_form_data(soup, otp):
    captcha = get_captcha_from_page(soup)
    form_data = {}
    form_data['ctl00$ContentPlaceHolder1$txtotp1'] = otp[0]
    form_data['ctl00$ContentPlaceHolder1$txtotp2'] = otp[1]
    form_data['ctl00$ContentPlaceHolder1$txtotp3'] = otp[2]
    form_data['ctl00$ContentPlaceHolder1$txtotp4'] = otp[3]
    form_data['ctl00$ContentPlaceHolder1$txtotp5'] = otp[4]
    form_data['ctl00$ContentPlaceHolder1$txtotp6'] = otp[5]
    form_data['ctl00$ContentPlaceHolder1$txtCaptchaMtr'] = captcha
    form_data['ctl00$ContentPlaceHolder1$btnOTP'] = 'Verify OTP'
    return form_data


def login(phone_num, password):
    login_url = base_url + 'Login.aspx'
    web_data = session.get(login_url)
    if not web_data.ok:
        raise Exception('failed to get login page')
    html_text = web_data.text
    soup = BeautifulSoup(html_text, 'html.parser')
    form_data = get_form_data(soup)
    form_data.update(get_login_form_data(soup, phone_num, password))
    logger.debug(f'login form data:\n{pformat(form_data)}')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    resp = session.post(login_url, data=form_data, headers=headers)
    logger.debug(f'status_code = {resp.status_code}\n headers:\n{pformat(resp.headers)}')
    if not resp.ok:
        raise Exception('login failed')
    soup = BeautifulSoup(resp.text, 'html.parser')
    span = soup.find('span', { 'id': 'ContentPlaceHolder1_lblMsg' })
    if span is not None:
        raise Exception(f'{span.text}')
    return resp


def login_otp(otp):
    login_otp_url = base_url + 'LoginOTP.aspx'
    web_data = session.get(login_otp_url)
    if not web_data.ok:
        raise Exception('failed to get login otp page')
    html_text = web_data.text
    soup = BeautifulSoup(html_text, 'html.parser')
    form_data = get_form_data(soup)
    form_data.update(get_login_otp_form_data(soup, otp))
    logger.debug(f'login otp form data:\n{pformat(form_data)}')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    resp = session.post(login_otp_url, data=form_data, headers=headers)
    logger.debug(f'status_code = {resp.status_code}\n headers:\n{pformat(resp.headers)}')
    if not resp.ok:
        raise Exception('login otp failed')
    if resp.url.endswith('Errorpage.aspx'):
        with open('login_fail.html', 'w') as f:
            f.write(resp.text)
        raise Exception('login failed')
    soup = BeautifulSoup(resp.text, 'html.parser')
    span = soup.find('span', { 'id': 'ContentPlaceHolder1_lblMsgOTPAttempt' })
    if span is not None:
        raise Exception(f'{span.text}')
    return resp


def login_wrap(phone_num, password, otp_from_pb):
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
    success_phase_1 = False
    if otp_from_pb:
        otp_listener = setup_otp_listener()
    while count < MAX_CAPTCHA_ATTEMPTS:
        try:
            logger.info('attempting a login')
            login(phone_num, password)
            success_phase_1 = True
            logger.info('login password phase done')
            break
        except Exception as ex:
            if str(ex) != FAILED_CAPTCHA:
                if otp_from_pb:
                    otp_listener.close()
                raise ex
            logger.warning('captcha failed..')
            count += 1

    if not success_phase_1:
        if otp_from_pb:
            otp_listener.close()
        raise Exception('login failed because of captcha errors')

    if otp_from_pb:
        otp = get_otp_pb(otp_listener, timeout=300)
    else:
        otp = get_otp_manual()
    if otp is None:
        raise Exception('Unable to get OTP')

    success = False
    while count < MAX_CAPTCHA_ATTEMPTS:
        try:
            logger.info('entering the login otp')
            login_otp(otp)
            ensure_dir(saved_cookie_file)
            logger.info('saving cookies to file')
            with open(saved_cookie_file, 'wb') as f:
                pickle.dump(session.cookies, f)
            success = True
            logger.info('login otp phase done')
            break
        except Exception as ex:
            if str(ex) != FAILED_CAPTCHA:
                raise ex
            logger.warning('captcha failed..')
            count += 1

    if not success:
        raise Exception('login failed because of captcha errors')


