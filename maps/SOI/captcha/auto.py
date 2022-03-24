import os
import logging
import glob

from pathlib import Path

import cv2
import pytesseract
import numpy as np

from PIL import Image, ImageOps
from imgcat import imgcat

img_data_dir = 'data/captcha/imgs/'

logger = logging.getLogger(__name__)

SHOW_IMG = (os.environ.get('SHOW_IMG', None) == "1")

def thresholding_cv(cv_image, inv=True):
    blocksize = 15
    c = 2
    binary_flag = cv2.THRESH_BINARY_INV if inv else cv2.THRESH_BINARY 
    fg = 255 if inv else 0
    #ret, thresh = cv2.threshold(cv_image, 0, 255, cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)
    thresh = cv2.adaptiveThreshold(cv_image, fg, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, binary_flag, blocksize, c)
    return thresh

def thresholding(img):
    cv_image = np.array(img)
    thresh_cv = thresholding_cv(cv_image)
    return Image.fromarray(thresh_cv)



def remove_transparency(im, bg_colour=(255, 255, 255)):

    # Only process if image has transparency (http://stackoverflow.com/a/1963146)
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):

        # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
        alpha = im.convert('RGBA').split()[-1]

        # Create a new background image of our matt color.
        # Must be RGBA because paste requires both images have the same format
        # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
        bg = Image.new("RGBA", im.size, bg_colour + (255,))
        bg.paste(im, mask=alpha)
        return bg

    else:
        return im


def guess(filename, models_dir):
    tessdir_base = models_dir

    tessdir_old = str(Path(tessdir_base).joinpath('old'))
    tessdir_new = str(Path(tessdir_base).joinpath('lstm'))
    config_base = ' --oem {} --psm {} --tessdata-dir "{}" configfile myconfig'
    #config_old = config_base.format(0, 7, tessdir_old)
    config_new = config_base.format(1, 7, tessdir_new)

    config = config_new
    #config = config_old

   #logger.info(f'{guessed_old=}, {guessed_new=}')


    image = Image.open(filename)
    #print_image(image)
    image = remove_transparency(image)
    image = image.convert('RGB')
    image = image.convert('L')
    image = thresholding(image)
    if SHOW_IMG:
        imgcat(image)
    width, height = image.size
    ideal_height = 32
    scale_factor = float(ideal_height)/float(height)
    image = ImageOps.scale(image, scale_factor)

    cv_image = np.array(image)
    esize = 2
    iterations = 1
    element = cv2.getStructuringElement(cv2.MORPH_RECT,
                                        (esize, esize),
                                        (-1, -1))
    cv_image = cv2.erode(cv_image, element, iterations=iterations)
    cv_image = cv2.copyMakeBorder(cv_image, 2, 2, 2, 2, cv2.BORDER_CONSTANT, None, 0)
    #cv_image = thresholding_cv(cv_image, inv=False)
    image = Image.fromarray(cv_image)

    if SHOW_IMG:
        imgcat(image)
    guessed = pytesseract.image_to_string(image, config=config)
    guessed = ''.join([ x for x in guessed if x in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' ])
    return guessed


def save_captcha(tempfile):
    counter_fname = Path(img_data_dir).joinpath('counter')
    if not Path(counter_fname).exists():
        with open(counter_fname, 'w') as f:
            f.write('1')
    with open(counter_fname, 'r') as f:
        counter = int(f.read().strip())

    contents = tempfile.getvalue()
    new_filename = Path(img_data_dir).joinpath(f'{counter}.jpeg')
    with open(new_filename, 'wb') as f:
        f.write(contents)

    with open(counter_fname, 'w') as f:
        f.write(str(counter + 1))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    model_dir = 'data/captcha/models/'
    imgs_dir = 'data/captcha/imgs/'
    filenames = glob.glob(imgs_dir + '*.jpeg')
    filenames = [ 'data/captcha/imgs/1.jpeg' ]
    for filename in filenames:
        logger.info(f'handling {filename}')
        guess(filename, model_dir)
