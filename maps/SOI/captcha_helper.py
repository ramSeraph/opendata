import os
import io
import logging

from pathlib import Path
from PIL import Image
from imgcat import imgcat

from captcha.auto import guess, save_captcha
from common import session, base_url

logger = logging.getLogger(__name__)

CAPTCHA_MANUAL = (os.environ.get('CAPTCHA_MANUAL', '0') == '1')
captcha_model_dir = 'data/captcha/models'

def guess_manual(filename):
    save_captcha(filename)
    image = Image.open(filename)
    imgcat(image)
    captcha_code = input("Enter the captcha: ")
    return captcha_code.strip()


def captcha_guess(filename, captcha_model_dir):
    if CAPTCHA_MANUAL:
        return guess_manual(filename)
    else:
        return guess(filename, captcha_model_dir)


def get_captcha(captcha_url):
    web_data = session.get(captcha_url)
    if not web_data.ok:
        raise Exception(f'unable to retrieve captcha at {captcha_url}')

    captcha_content = web_data.content
    tempfile = io.BytesIO(captcha_content)
    #save_captcha(filename)
    captcha_code = captcha_guess(tempfile, captcha_model_dir)
    logger.info(f'gueesed captcha as {captcha_code}')
    return captcha_code


def get_captcha_from_page(soup):
    div = soup.find('div', { 'class': 'captcha' })
    img = div.find('img')
    captcha_url = img.attrs['src']
    captcha_url = base_url + captcha_url
    captcha = get_captcha(captcha_url)
    return captcha


def check_captcha_models(models_pathname):

    models_path = Path(models_pathname)
    # hardcoding list of files here so as to not hit the network everytime
    paths = []
    paths.append(models_path.joinpath('lstm', 'eng.traineddata'))
    paths.append(models_path.joinpath('lstm', 'osd.traineddata'))
    paths.append(models_path.joinpath('old', 'eng.traineddata'))
    paths.append(models_path.joinpath('old', 'myconfig'))
    missing_files = any([not path.exists() for path in paths])

    if missing_files:
        logging.error(f'missing model files: {missing_files}')
        script_file = Path(__file__).parent / 'util' / 'download_captcha_models.sh'
        script_filename = str(script_file)
        logging.error(f'to get the models run {script_filename} {models_pathname}')
        raise Exception('missing captcha model files')
