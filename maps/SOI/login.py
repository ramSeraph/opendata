import re
import hashlib
import logging

from pprint import pformat

from bs4 import BeautifulSoup

from captcha_helper import get_captcha_from_page
from common import base_url, get_form_data, session

logger = logging.getLogger(__name__)


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


