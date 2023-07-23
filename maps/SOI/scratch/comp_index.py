import glob
from pathlib import Path

from PIL import Image, ImageOps
from imgcat import imgcat
import pytesseract
import cv2
import numpy as np

# script to OCR the compiation index of SOI sheets, used but haven't bothered to integrate

SHOW_IMG=True
captcha_model_dir = 'data/captcha/models'

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


def ocr_text_area(text_img_file, new=True, force=False, blur=True, save=True):
    tessdir_base = captcha_model_dir

    tessdir_old = str(Path(tessdir_base).joinpath('old'))
    tessdir_new = str(Path(tessdir_base).joinpath('lstm'))
    config_base = ' --oem {} --psm {} --tessdata-dir "{}"'
    config_old = config_base.format(0, 6, tessdir_old)
    config_new = config_base.format(1, 6, tessdir_new)
    config = config_new if new else config_old
    text_file = text_img_file.replace('.jpg', '.txt')
    if Path(text_file).exists() and not force:
        text = Path(text_file).read_text()
        print(f'{text_img_file}:')
        print(text)
        return text

    img = cv2.imread(str(text_img_file))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = thresholding_cv(img)
    print(f'{img.shape=}')
    h, w = img.shape
    sf = h/310.0
    if sf > 1.5:
        dim = [ int(w/sf), int(h/sf) ]
        img = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
    if SHOW_IMG:
        imgcat(Image.fromarray(img))

    if blur:
        blur_kern = 3
        img = cv2.medianBlur(img, blur_kern)
        if SHOW_IMG:
            imgcat(Image.fromarray(img))
    guessed = pytesseract.image_to_string(img, config=config)
    print(guessed)
    if save:
        Path(text_file).write_text(guessed)
    return guessed


#filenames = glob.glob('data/inter/*/ctext.jpg')
#Path('data/ctext_list.txt').write_text('\n'.join(filenames))
filenames = Path('data/ctext_list.txt').read_text().split('\n')
filenames = [ f.strip() for f in filenames ]
#filenames = ['data/inter/65J_12/ctext.jpg']
for filename in filenames:
    #text = ocr_text_area(filename, new=True, force=False)
    text = ocr_text_area(filename, new=False, force=True, blur=True, save=True)
