#import copy
import logging

from pathlib import Path

#from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
#from pdfminer.pdfpage import PDFPage
#from pdfminer.converter import PDFLayoutAnalyzer
#from pdfminer.high_level import extract_text_to_fp

#from pdf2image import convert_from_path
#import cv2
#from PIL import Image

from .common import (get_url, get_page_soup,
                     get_links_from_map_page,
                     ensure_dir, drill_down_and_download)

logger = logging.getLogger(__name__)


def get_block_graphs(executor, url):
    soup, cookie = get_page_soup(get_url(url), True)
    map_infos = get_links_from_map_page(soup)
    headers = {
        'Cookie': cookie
    }
    for map_info in map_infos:
        drill_down_and_download(map_info, headers, 'block_graphs')
        

#def show_grayscale(cv_img):
#    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2BGR)
#    p_img = Image.fromarray(cv_img)
#    imgcat(p_img)


def parse_block_graphs(executor):
    pass
    #filenames = glob.glob('data/raw/block_graphs/*/*/*.pdf')
    #for filename in filenames:
    #    print('processing {}'.format(filename))
    #    images = convert_from_path(filename)
    #    print('found {} images'.format(len(images)))
    #    for image in images:
    #        # find all text
    #        # detect and remove it.. but keep coordinates
    #        image = image.convert('RGB')
    #        image = np.array(image)
    #        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    #        #original = image
    #        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #        ret, thresh1 = cv2.threshold(image, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
    #        show_grayscale(thresh1)
    #        rect_size = 5
    #        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (rect_size, rect_size))
    #        dilation = cv2.dilate(thresh1, rect_kernel, iterations = 1)
    #        show_grayscale(dilation)
    #        contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    #        #show_grayscale(contours)



    #        #show_grayscale(image)
    #        #edges = cv2.Canny(image, 30, 100)
    #        #show_grayscale(edges)

    #        #cv2.imshow("edges", edges)
    #        #imgcat(image)
    #        #exit()



#TODO: get last update times


