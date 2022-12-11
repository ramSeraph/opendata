import os
import shutil
import json
import glob
import time
import zipfile
import subprocess
from pathlib import Path
from functools import cmp_to_key
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

import cv2
import imutils
import numpy as np
from PIL import Image
from imgcat import imgcat

from pdfminer.image import ImageWriter
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTImage
from pdfminer.pdftypes import resolve_all, PDFObjRef, PDFNotImplementedError

from PyPDF2 import PdfFileReader

from shapely.geometry import LineString, LinearRing, Polygon, CAP_STYLE, JOIN_STYLE
from shapely.wkt import loads as wkt_loads
from shapely.wkt import dumps as wkt_dumps
from shapely.affinity import translate

from rasterio.crs import CRS
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps, rowcol

from pyproj.aoi import AreaOfInterest
from pyproj.transformer import Transformer
from pyproj.database import query_utm_crs_info

from known_problems import known_problems

os.environ['PATH'] = './bin:' + os.environ.get('PATH', '')

# remove decompression_bomb_check
Image.MAX_IMAGE_PIXELS = None

DELETE_INTERMEDIATES = False
USE_4326 = False
SHOW_IMG = os.environ.get('SHOW_IMG', '0') == '1'

inter_dir = 'data/inter'

def get_file_dir(filename):
    file_p = Path(filename)
    sheet_no = file_p.name.replace('.pdf', '')
    dir_p = Path(inter_dir).joinpath(sheet_no)
    dir_p.mkdir(parents=True, exist_ok=True)
    return dir_p



# from camelot.. too slow for a big image
def find_lines(
    threshold, direction="horizontal", line_scale=15, iterations=0
):
    lines = []

    if direction == "vertical":
        size = threshold.shape[0] // line_scale
        el = cv2.getStructuringElement(cv2.MORPH_RECT, (1, size))
    elif direction == "horizontal":
        size = threshold.shape[1] // line_scale
        el = cv2.getStructuringElement(cv2.MORPH_RECT, (size, 1))
    elif direction is None:
        raise ValueError("Specify direction as either 'vertical' or 'horizontal'")

    threshold = cv2.erode(threshold, el)
    #imgcat(Image.fromarray(threshold))
    threshold = cv2.dilate(threshold, el)
    dmask = cv2.dilate(threshold, el, iterations=iterations)
    #imgcat(Image.fromarray(dmask))

    contours, _ = cv2.findContours(
        threshold.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        x1, x2 = x, x + w
        y1, y2 = y, y + h
        if direction == "vertical":
            lines.append(((x1 + x2) // 2, y2, (x1 + x2) // 2, y1))
        elif direction == "horizontal":
            lines.append((x1, (y1 + y2) // 2, x2, (y1 + y2) // 2))

    return dmask, lines

def print_proj(proj):
    print(f'len - {len(proj)}')
    splits = np.array_split(proj, round(len(proj)/50))
    counter = 0
    for split in splits:
        print(f'{counter:05}', ' - ', *split)
        counter += len(split)


def get_projection(img_mask, axis):
    proj = np.count_nonzero(img_mask, axis=axis)
    return proj


def get_color_mask(img_hsv, color):
    if not isinstance(color, list):
        colors = [color]
    else:
        colors = color

    img_masks = []
    for color in colors:
        if color == 'pink':
            lower = np.array([140, 74, 76])
            upper = np.array([166, 255, 255])
        elif color == 'pinkish':
            lower = np.array([130, 40, 76])
            upper = np.array([170, 255, 255])
        elif color == 'black':
            lower = np.array([0, 0, 0])
            upper = np.array([179, 255, 80])
        elif color == 'grey':
            lower = np.array([0, 0, 50])
            upper = np.array([179, 10, 120])
        elif color == 'greyish':
            lower = np.array([0, 0, 50])
            upper = np.array([179, 130, 145])
        elif color == 'white':
            lower = np.array([0, 0, 230])
            upper = np.array([179, 6, 255])
        elif color == 'green':
            lower = np.array([50, 100, 100])
            upper = np.array([70, 255, 255])
        elif color == 'red1':
            lower = np.array([0, 50, 50])
            upper = np.array([10, 255, 255])
        elif color == 'red2':
            lower = np.array([165, 50, 50])
            #lower = np.array([170, 50, 50])
            upper = np.array([180, 255, 255])
        elif color == 'blue':
            lower = np.array([100, 50, 0])
            upper = np.array([140, 255, 255])
        else:
            raise Exception(f'{color} not handled')
        img_mask = cv2.inRange(img_hsv, lower, upper)
        img_masks.append(img_mask)

    final_mask = img_masks[0]
    for img_mask in img_masks[1:]:
        orred = np.logical_or(final_mask, img_mask)
        final_mask = orred

    return final_mask


def get_ext_count(point, img_mask, ext_thresh, factor, cwidth):
    x, y = point
    h, w = img_mask.shape[:2]
    uc = 0
    ext_length = 10*factor
    ye = min(y+ext_length, h - 1)
    print(ye)
    uc += np.count_nonzero(img_mask[y:ye, x])
    for i in range(cwidth):
        uc += np.count_nonzero(img_mask[y:ye, x+i])
        uc += np.count_nonzero(img_mask[y:ye, x-i])

    dc = 0
    ye = max(y-ext_length, 0)
    dc += np.count_nonzero(img_mask[ye:y, x])
    for i in range(cwidth):
        dc += np.count_nonzero(img_mask[ye:y, x+i])
        dc += np.count_nonzero(img_mask[ye:y, x-i])

    lc = 0
    xe = min(x+ext_length, w - 1)
    lc += np.count_nonzero(img_mask[y, x:xe])
    for i in range(cwidth):
        lc += np.count_nonzero(img_mask[y+i, x:xe])
        lc += np.count_nonzero(img_mask[y-i, x:xe])

    rc = 0
    xe = max(x-ext_length, 0)
    rc += np.count_nonzero(img_mask[y, xe:x])
    for i in range(cwidth):
        rc += np.count_nonzero(img_mask[y+i, xe:x])
        rc += np.count_nonzero(img_mask[y-i, xe:x])

    counts = [ uc, dc, rc, lc ]
    print(f'{point=}, {counts=}, {ext_thresh=} {factor=}')
    exts = [ c > ext_thresh*factor*(2*cwidth + 1)/3 for c in counts ]
    return exts.count(True)
 


def show_contours(o_bimg, contours):
    b = o_bimg.copy()
    rgb = cv2.merge([b*255,b*255,b*255])
    cv2.drawContours(rgb, contours, -1, (0, 255, 0), 2, cv2.LINE_AA)
    if SHOW_IMG:
        imgcat(Image.fromarray(rgb))
    #cv2.imwrite('temp.jpg', rgb)

def get_breaks(proj, min_val=0):
    breaks = []
    s = None
    for i, v in enumerate(proj):
        if v > min_val:
            if s is not None:
                breaks.append((s, i))
                s = None
        else:
            if s is None:
                s = i
    if s is not None:
        breaks.append((s, i))

    return breaks



def get_images(layout):
    imgs = []
    if isinstance(layout, LTImage):
        imgs.append(layout)

    objs = getattr(layout, '_objs', [])
    for obj in objs:
        imgs.extend(get_images(obj))
    return imgs


def run_external(cmd):
    print(f'running cmd - {cmd}')
    start = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    print(f'STDOUT: {res.stdout}')
    print(f'STDERR: {res.stderr}')
    print(f'command took {end - start} secs to run')
    if res.returncode != 0:
        raise Exception(f'command {cmd} failed with exit code: {res.returncode}')


def crop_img(img, bbox):
    x, y, w, h = bbox
    return img[y:y+h, x:x+w]


def scale_bbox(bbox, rw, rh):
    b = bbox
    return (int(b[0]*rw), int(b[1]*rh), int(b[2]*rw), int(b[3]*rh))

def scale_point(point, rw, rh):
    return [int(point[0]*rw), int(point[1]*rh)]

def translate_bbox(bbox, ox, oy):
    b = bbox
    return (b[0] + ox, b[1] + oy, b[2], b[3])

def round_off(geom):
    coords_arrays = geom['coordinates']
    for coords in coords_arrays:
        for coord in coords:
            coord[0] = round(coord[0], 5)
            coord[1] = round(coord[1], 5)


index_map = None
def get_full_index():
    global index_map
    if index_map is not None:
        return index_map
    print('loading index file')
    with open('data/index.geojson', 'r') as f:
        index = json.load(f)
    index_map = {}
    for f in index['features']:
        sheet_no = f['properties']['EVEREST_SH']
        geom = f['geometry']
        index_map[sheet_no] = geom
    return index_map
    
def split_line(p1, p2):
    #TODO: might need to use projections
    line = LineString([p1, p2])
    pts = [line.interpolate(i/6, normalized=True).coords[0] for i in range(0, 7)]
    pts = [ (round(x[0]), round(x[1])) for x in pts ]
    return pts


def get_utm_crs(c_long, c_lat):
    utm_crs_list = query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=AreaOfInterest(
            west_lon_degree=c_long,
            south_lat_degree=c_lat,
            east_lon_degree=c_long,
            north_lat_degree=c_lat
        ),
    )
    utm_crs = CRS.from_epsg(utm_crs_list[0].code)
    return utm_crs

def fill_tif(k, k_dir):
    full_index = get_full_index()
    geom = full_index[k.replace('_', '/')]
    kbox = geom['coordinates'][0]
    kbox_poly = Polygon(kbox)
    print(f'{kbox_poly.centroid.coords[0]=}')
    src_crs = get_utm_crs(*kbox_poly.centroid.coords[0])
    box_crs = CRS.from_epsg(4326)
    transformer = Transformer.from_crs(box_crs, src_crs, always_xy=True)
    kbox = [ transformer.transform(*c) for c in kbox ]
    vrt_file = k_dir.joinpath('final.vrt')
    new_final_file = k_dir.joinpath('new_final.tif')
    run_external(f'gdalbuildvrt -tr 1 1 -te {kbox[0][0]} {kbox[1][1]} {kbox[2][0]} {kbox[0][1]} {str(vrt_file)} {str(final_file)}')
    run_external(f'gdal_translate {str(vrt_file)} {str(new_final_file)}')


def reorder_poly_points(poly_points):
    # sort points in anti clockwise order
    num_corners = len(poly_points)
    box = LinearRing(poly_points + [poly_points[0]])
    if not box.is_ccw:
        poly_points = poly_points.copy()
        poly_points.reverse()

    center = box.centroid.coords[0]
    #print(center)
    indices = range(0, num_corners)
    indices = [ i for i in indices if poly_points[i][0] < center[0] and poly_points[i][1] < center[1] ]
    def cmp(ci1, ci2):
        c1 = poly_points[ci1]
        c2 = poly_points[ci2]
        if c1[1] == c2[1]:
            return c2[0] - c1[0]
        else:
            return c2[1] - c1[1]

    s_indices = sorted(indices, key=cmp_to_key(cmp), reverse=True)
    #print(f'{s_indices=}')
    first = s_indices[0]
    poly_reordered = [ poly_points[first] ]
    for i in range(1, num_corners):
        idx = (first - i) % num_corners
        poly_reordered.append(poly_points[idx])
    #print(f'{poly_reordered=}')
    return poly_reordered


class Converter:
    def __init__(self, filename, extra={}, extra_ancillary={}):
        self.filename = filename
        self.file_fp = None
        self.file_dir = get_file_dir(filename)
        self.cur_step = None
        self.small_img = None
        self.full_img = None
        self.map_img = None
        self.flavor = None
        self.pdf_document = None
        self.mapbox_corners = None
        self.src_crs = None
        self.extra_ancillary = extra_ancillary
        self.find_line_iter = extra.get('find_line_iter', 1)
        self.find_line_scale = extra.get('find_line_scale', 3)
        self.ext_thresh_ratio = extra.get('ext_thresh_ratio', 20.0 / 18000.0)
        self.pdf_rotate = extra.get('pdf_rotate', 0)
        self.use_bbox_area = extra.get('use_bbox_area', True)
        self.line_color = extra.get('line_color', ['black', 'greyish'])
        self.band_color = extra.get('band_color', 'pinkish')
        self.sb_color = extra.get('sb_color', self.band_color)
        self.sb_break_min_val = extra.get('sb_break_min_val', 2)
        self.sb_left = extra.get('sb_left', True)
        self.auto_rotate_thresh = extra.get('auto_rotate_thresh', 0.7)
        self.corner_overrides = extra.get('corner_overrides', None)
        self.shrunk_map_area_corners = extra.get('shrunk_map_area_corners', None)
        self.extents = extra.get('extents', None)
        self.jpeg_export_quality = extra.get('jpeg_export_quality', 10)
        #self.grid_line_buf = extra.get('grid_line_buf', None)
        self.grid_lines = extra.get('grid_lines', None)
        self.poly_approx_factor = extra.get('poly_approx_factor', 0.001)
        self.cwidth = extra.get('cwidth', 1)
        self.collar_erode = extra.get('collar_erode', 0)



    def get_full_img_file(self):
        return Path(self.file_dir).joinpath('full.jpg')

    def get_pdf_doc(self):
        self.file_fp = open(self.filename, "rb")
        parser = PDFParser(self.file_fp)
        document = PDFDocument(parser)
        return document


    def get_flavor(self):
        if self.flavor is not None:
            return self.flavor
        flav_file = Path(self.file_dir).joinpath('flav.txt')
        if flav_file.exists():
            self.flavor = flav_file.read_text().strip()
            return self.flavor

        document = self.get_pdf_doc()
        doc_producer = document.info[0]['Producer'].decode('utf8')
        if 'Image Conversion Plug-in' in doc_producer:
            flavor = 'Image PDF'
        elif 'Acrobat Distiller' in doc_producer:
            flavor = 'Distiller'
        elif 'PDFOut' in doc_producer:
            flavor = 'PDFOut'
        elif 'Adobe Photoshop' in doc_producer:
            flavor = 'Photoshop'
        elif 'www.adultpdf.com' in doc_producer:
            flavor = 'Adultpdf'
        elif 'GPL Ghostscript' in doc_producer:
            flavor = 'Ghostscript'
        elif 'Adobe PDF Library' in doc_producer:
            flavor = 'Microstation'
        else:
            print(document.info)
            raise Exception('Unknown flavor')
 
        flav_file.write_text(flavor)
        self.flavor = flavor
        return flavor


    def image_pdf_extract(self):
        document = self.get_pdf_doc()
     
        if not document.is_extractable:
            raise PDFTextExtractionNotAllowed(
                    "Text extraction is not allowed"
            )
        img_writer = ImageWriter('.')
        rsrcmgr = PDFResourceManager(caching=True)
        device = PDFPageAggregator(rsrcmgr, laparams=None)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        page_info = {}
        pno = 0
        for page in PDFPage.create_pages(document):
            if pno > 0:
                raise Exception('only one page expected')
            interpreter.process_page(page)
            layout = device.get_result()
            page_info = {}
            page_info['layout'] = layout
            images = get_images(layout)
            if len(images) > 1:
                raise Exception('Only one image expected')
            image = images[0]
            print(image)
            print(image.colorspace)

            # fix to pdfminer bug
            if len(image.colorspace) == 1 and isinstance(image.colorspace[0], PDFObjRef):
                image.colorspace = resolve_all(image.colorspace[0])
                if not isinstance(image.colorspace, list):
                    image.colorspace = [ image.colorspace ]

            print(image.colorspace)
            try:
                fname = img_writer.export_image(image)
                print(f'image extracted to {fname}')
                out_filename = str(self.get_full_img_file())
                print(f'writing {out_filename}')
                if fname.endswith('.bmp') or fname.endswith('.img'):
                    # give up
                    Path(fname).unlink()
                    self.convert_pdf_to_image()
                else:
                    shutil.move(fname, out_filename)
            except PDFNotImplementedError:
                self.convert_pdf_to_image()
            pno += 1


    def convert_pdf_to_image(self, size_hint=18000):
        inp = PdfFileReader(open(self.filename, 'rb'))
        page = inp.getPage(0)
        bbox = page.mediaBox
        print(f'Advertised ROTATE: {page.get("/Rotate")}')
        rotate = self.pdf_rotate
        print(f'ROTATE: {rotate}')
        w, h = bbox.getWidth(), bbox.getHeight()
        ow = size_hint
        oh = round(float(h) * float(ow) / float(w))
        img_filename = str(self.get_full_img_file())
        print('converting pdf to image using mupdf')
        #run_external(f'mutool draw -w {ow} -h {oh} -c rgb -o {img_filename} {self.filename}')
        run_external(f'mutool draw -n data/SOI_FONTS -w {ow} -h {oh} -c rgb -o {img_filename} {self.filename}')
        if rotate == 90 or rotate == 270:
            print('rotating image')
            img = cv2.imread(img_filename)
            img_rotate = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE if rotate == 90 else cv2.ROTATE_90_COUNTERCLOCKWISE)
            rotate_filename = img_filename.replace('.jpg', '.rotated.jpg')
            cv2.imwrite(rotate_filename, img_rotate)
            shutil.move(rotate_filename, img_filename)


        #print('converting pdf to image using ghostscript')
        #run_external(f'gs -g{ow}x{oh} -dBATCH -dNOPAUSE -dDOINTERPOLATE -sPageList=1 -sOutputFile={img_filename} -sDevice=jpeg {self.filename}')
        #print('converting pdf to image using pdftocairo')
        ##run_external(f'pdftocairo -antialias best -singlefile -r 72 -scale-to 18000 -jpeg {self.filename}')
        #exp_out_file = Path(self.filename).name.replace('.pdf', '.jpg')
        #shutil.move(exp_out_file, img_filename)


    def convert(self, size_hint=18000):
        img_file = self.get_full_img_file()
        if img_file.exists():
            print(f'file {img_file} exists.. skipping conversion')
            return
    
        flavor = self.get_flavor()
        if flavor in ['Image PDF', 'Photoshop']:
            self.image_pdf_extract()
        else:
            self.convert_pdf_to_image(size_hint)


    def get_full_img(self):
        if self.full_img is not None:
            return self.full_img
        
        img_file = self.get_full_img_file()
        print('loading full image')
        start = time.time()
        self.full_img = cv2.imread(str(img_file))
        end = time.time()
        print(f'loading image took {end - start} secs')
        return self.full_img



    def get_shrunk_img(self):
        if self.small_img is not None:
            return self.small_img
        small_img_file = self.file_dir.joinpath('small.jpg')
        if small_img_file.exists():
            self.small_img = cv2.imread(str(small_img_file))
            return self.small_img

        sw = 1800

        img = self.get_full_img()
        h, w = img.shape[:2]

        r = float(sw) / w
        dim = (int(h*r), sw)
        small_img = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(small_img_file), small_img)

        # for some reason this fixes some of the issues
        self.small_img = cv2.imread(str(small_img_file))
        return self.small_img


    def get_map_img(self):
        if self.map_img is not None:
            return self.map_img
        mapbox_file = self.file_dir.joinpath('mapbox.jpg')
        self.map_img = cv2.imread(str(mapbox_file))
        return self.map_img
        


    def get_maparea(self):
        img = self.get_shrunk_img()
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        img_mask = get_color_mask(img_hsv, self.band_color)
        if self.shrunk_map_area_corners is not None:
            map_contour = np.array(self.shrunk_map_area_corners).reshape((-1,1,2)).astype(np.int32)
        else:
            start = time.time()
            img_mask_g = img_mask.astype(np.uint8)*255
            if self.collar_erode != 0:
                el1 = cv2.getStructuringElement(cv2.MORPH_RECT, (1, self.collar_erode))
                #el2 = cv2.getStructuringElement(cv2.MORPH_RECT, (self.collar_erode, 1))
                img_mask_g = cv2.erode(img_mask_g, el1)
                #img_mask_g = cv2.erode(img_mask_g, el2)
            if SHOW_IMG:
                imgcat(Image.fromarray(img_mask_g))
            print(f'getting {self.band_color} contours for whole image')
            contours, hierarchy = cv2.findContours(
                img_mask_g, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
            )
            ctuples = list(zip(list(contours), list(hierarchy[0])))
            end = time.time()
            print(f'pink contours took {end - start} secs')
            show_contours(img_mask_g, [x[0] for x in ctuples])
            if self.use_bbox_area:

                def get_bbox_area(ctuple):
                    bbox = cv2.boundingRect(ctuple[0])
                    return bbox[2] * bbox[3]

                ctuples_s = sorted(ctuples, key=get_bbox_area, reverse=True)
                map_contour = ctuples_s[0][0]
            else:
                ctuples_s = sorted(ctuples, key=lambda x: cv2.contourArea(x[0]), reverse=True)
                #print(ctuples_s[0])
                map_inner_contour_idx = ctuples_s[0][1][2]
                map_contour = ctuples[map_inner_contour_idx][0]
                #map_contour = ctuples_s[0][0]
        map_bbox = cv2.boundingRect(map_contour)
        map_min_rect = cv2.minAreaRect(map_contour)
        print(f'{map_bbox=}')
        print(f'{map_min_rect=}')
        map_area = map_bbox[2] * map_bbox[3]
        h, w = img.shape[:2]
        total_area = w * h
        if total_area / map_area > 3:
            show_contours(img_mask, [map_contour])
            raise Exception(f'map area less than expected, {map_area=}, {total_area=}')
    
        return map_bbox, map_min_rect, map_contour

    def split_sidebar_area(self, img):
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, w = img_hsv.shape[:2]
        img_mask = get_color_mask(img_hsv, self.sb_color) 
        print(f'getting {self.sb_color} contours for sidebar image')
        contours, _ = cv2.findContours(
            img_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        #show_contours(img_mask, contours)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        def is_wide(c):
            b = cv2.boundingRect(c)
            bw, bh = b[2], b[3]
            return bw/bh > 2
        contours = [ c for c in contours if is_wide(c) ]
        top_2 = contours[:2]
        #show_contours(img_mask, top_2)
        #TODO: add some check if we got this right
        # both should of similar area?
        top_2_bboxes = [ cv2.boundingRect(c) for c in top_2 ]
        top_2_bboxes = sorted(top_2_bboxes, key=lambda b: b[1])
        b1, b2 = top_2_bboxes
    
        y1 = b1[1] + b1[3] + 1
        y2 = b2[1] - 1
        y3 = b2[1] + b2[3] + 1
        x1 = min(b1[0], b2[0])
        x2 = max(b1[0] + b1[2], b2[0] + b2[2])
    
        legend_bbox = (x1, y1, x2 - x1, y2 - y1)
        rest_bbox = (x1, y3, x2 - x1, h - y3)
    
        #legend_hsv = crop_img(img_hsv, legend_bbox)
        #imgcat(Image.fromarray(cv2.cvtColor(legend_hsv, cv2.COLOR_HSV2RGB)))
    
        #rest_hsv = crop_img(img_hsv, rest_bbox)
        #imgcat(Image.fromarray(cv2.cvtColor(rest_hsv, cv2.COLOR_HSV2RGB)))
        #rest_img_mask = get_color_mask(rest_hsv, ['black', 'grey'])
        #imgcat(Image.fromarray(rest_img_mask.astype(np.uint8)*255))
    
        return legend_bbox, rest_bbox



    def get_shrunk_splits(self):
        shrunk_splits_file = self.file_dir.joinpath('shrunk_splits.json')
        if shrunk_splits_file.exists():
            with open(shrunk_splits_file, 'r') as f:
                shrunk_splits = json.load(f)
            return shrunk_splits

        map_bbox, _, map_contour = self.get_maparea()
        perimeter_len = cv2.arcLength(map_contour, True)
        print(f'{perimeter_len=}')
        epsilon = self.poly_approx_factor * perimeter_len
        map_poly = cv2.approxPolyDP(map_contour, epsilon, True)
        map_poly_points = [ list(p[0]) for p in map_poly ]
        print(f'{map_poly_points=}')
 
        mb = map_bbox
        small_img = self.get_shrunk_img()
        h, w = small_img.shape[:2]
        if self.sb_left:
            sbx, sby, sbw, sbh = (0, mb[1]-1,
                                  mb[0], mb[3])
        else:
            sbx, sby, sbw, sbh = (mb[0] + mb[2] + 1, mb[1]-1,
                                  w - mb[0] - mb[2], mb[3])
        sb_bbox = (sbx, sby, sbw, sbh)
        print(f'{sb_bbox=}')
    
        sb_img = crop_img(small_img, sb_bbox)
        legend_bbox, rest_bbox = self.split_sidebar_area(sb_img)
        legend_bbox = translate_bbox(legend_bbox, sbx, sby)
        rest_bbox = translate_bbox(rest_bbox, sbx, sby)

        full_img = self.get_full_img()
        fh, fw = full_img.shape[:2]
        rh, rw = float(fh)/float(h), float(fw)/float(w)

        bboxes = [ map_bbox, legend_bbox, rest_bbox ]
        full_bboxes = [ scale_bbox(bbox, rw, rh) for bbox in bboxes ]
        map_poly_points_scaled = [ scale_point(p, rw, rh) for p in map_poly_points ]
        bbox_dict = {
            'map': full_bboxes[0],
            'map_poly_points': map_poly_points_scaled,
            'legend': full_bboxes[1],
            'rest': full_bboxes[2],
        }
        with open(shrunk_splits_file, 'w') as f:
            json.dump(bbox_dict, f, indent=4)

        return bbox_dict
        

    def get_intersection_point(self, img_hsv, ext_thresh):
        img_mask = get_color_mask(img_hsv, self.line_color)
        img_mask_g = img_mask.astype(np.uint8)
        h, w = img_mask.shape[:2]
        img_mask_g = img_mask_g*255
        if SHOW_IMG:
            imgcat(Image.fromarray(img_mask_g))
    
        v_mask, v_lines = find_lines(img_mask_g, direction='vertical', line_scale=self.find_line_scale, iterations=self.find_line_iter)
        h_mask, h_lines = find_lines(img_mask_g, direction='horizontal', line_scale=self.find_line_scale, iterations=self.find_line_iter)
        #v_lines = [ l for l in v_lines if 0 < l[0] < w - 1 ]
        #h_lines = [ l for l in h_lines if 0 < l[1] < h - 1 ]
        print(f'{v_lines=}')
        print(f'{h_lines=}')
    
        ips = []
        only_lines = np.multiply(v_mask, h_mask)
        jcs, _ = cv2.findContours(only_lines, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        for j in jcs:
            #if len(jc) <= 4:  # remove contours with less than 4 joints
            #    continue
            jx, jy, jw, jh = cv2.boundingRect(j)
            c1, c2 = (2 * jx + jw) // 2, (2 * jy + jh) // 2
            if 0 < c1 < w - 1 and 0 < c2 < h - 1:
                ips.append((c1, c2))
    
    
        #res = np.where(only_lines == 1)
        #ips = list(zip(res[1], res[0]))
        print(f'{ips=}')
        #imgcat(Image.fromarray(only_lines*255))
    
        for pix_factor in [1, 2, 4, 8]:
            four_corner_ips = []
            for ip in ips:
                ext_count = get_ext_count(ip, img_mask, ext_thresh, pix_factor, self.cwidth)
                print(f'{ip=}, {ext_count}')
                if ext_count == 4:
                    four_corner_ips.append(ip)
    
            if len(four_corner_ips) == 0:
                raise Exception(f'no intersection points found - {len(four_corner_ips)}')

            if len(four_corner_ips) == 1:
                break

            if len(four_corner_ips) > 1:
                continue

        if len(four_corner_ips) > 1:
            raise Exception(f'multiple intersection points found - {len(four_corner_ips)}')

        return four_corner_ips[0]


    def locate_corners_generic(self, img_hsv, map_poly_points, corner_overrides):
        corner_ratio = 400.0 / 9000.0
        w = img_hsv.shape[1]
        h = img_hsv.shape[0]
        cw = round(corner_ratio * w)
        ch = round(corner_ratio * h)

        map_poly_points = reorder_poly_points(map_poly_points)
        print(f'{map_poly_points=}')
        num_corners = len(map_poly_points)
        box = LinearRing(map_poly_points + [map_poly_points[0]])
        buffered_poly = box.buffer(-cw/2, single_sided=True, join_style=JOIN_STYLE.mitre)
        inner_ring = buffered_poly.interiors[0]
        corner_centers = list(inner_ring.coords)
        corner_centers.reverse()
        print(f'{corner_centers=}')
        corner_boxes = []
        for c in corner_centers[:-1]:
            c = (int(c[0]), int(c[1]))
            corner_box = ((int(c[0] - cw/2), int(c[1] - cw/2)), (cw, cw))
            corner_boxes.append(corner_box)

        print(f'{corner_boxes=}')

        points = []
        for i, corner_box in enumerate(corner_boxes):
            corner_override = corner_overrides[i]
            if corner_override is not None:
                points.append(corner_override)
                continue
            print(f'{corner_box=}')
            bx, by = corner_box[0]
            bw, bh = corner_box[1]
            c_img = img_hsv[by:by+bh, bx:bx+bw]
            ipoint = self.get_intersection_point(c_img, self.ext_thresh_ratio * w)
            ipoint = bx + ipoint[0], by + ipoint[1]
            points.append(ipoint)
        return points


    def locate_corners(self, img_hsv, corner_overrides):
        corner_ratio = 400.0 / 9000.0
    
        w = img_hsv.shape[1]
        h = img_hsv.shape[0]
        cw = round(corner_ratio * w)
        ch = round(corner_ratio * h)
        y = h - 1 - ch
        x = w - 1 - cw
    
        print(f'main img dim: {w=}, {h=}')
        # take the four corners
        corner_boxes = []
        corner_boxes.append(((0, 0), (cw, ch)))
        corner_boxes.append(((0, y), (cw, ch)))
        corner_boxes.append(((x, y), (cw, ch)))
        corner_boxes.append(((x, 0), (cw, ch)))
    
        # get intersection points
        points = []
        for i, corner_box in enumerate(corner_boxes):
            corner_override = corner_overrides[i]
            if corner_override is not None:
                points.append(corner_override)
                continue
            bx, by = corner_box[0]
            bw, bh = corner_box[1]
            c_img = img_hsv[by:by+bh, bx:bx+bw]
            print(f'{corner_box=}')
            ipoint = self.get_intersection_point(c_img, self.ext_thresh_ratio * w)
            ipoint = bx + ipoint[0], by + ipoint[1]
            points.append(ipoint)
        return points


    def process_map_area(self, map_bbox, map_poly_points):
        mapbox_file = self.file_dir.joinpath('mapbox.jpg')
        full_file = self.file_dir.joinpath('full.jpg')
        corners_file = self.file_dir.joinpath('corners.json')
        if corners_file.exists():
            print('corners file exists.. shortcircuiting')
            return

        full_img = self.get_full_img()
        full_img_hsv = cv2.cvtColor(full_img, cv2.COLOR_BGR2HSV)
        map_img_hsv = crop_img(full_img_hsv, map_bbox)
        
        corner_overrides_full = self.corner_overrides
        if corner_overrides_full is None:
            corner_overrides_full = [ None ] * len(map_poly_points)
        corner_overrides = [ (c[0] - map_bbox[0], c[1] - map_bbox[1]) if c is not None else None for c in corner_overrides_full ]
        map_poly_points = [ (p[0] - map_bbox[0], p[1] - map_bbox[1]) for p in map_poly_points ]

        if self.extents is None:
            corners = self.locate_corners(map_img_hsv, corner_overrides)
        else:
            corners = self.locate_corners_generic(map_img_hsv, map_poly_points, corner_overrides)

        corners_contour = np.array(corners).reshape((-1,1,2)).astype(np.int32)
        bbox = cv2.boundingRect(corners_contour)
        print(f'{bbox=}')
        print(f'{corners=}')
        map_img_hsv = crop_img(map_img_hsv, bbox)
        print('writing the main mapbox file')
        self.map_img = cv2.cvtColor(map_img_hsv, cv2.COLOR_HSV2BGR)
        cv2.imwrite(str(mapbox_file), self.map_img)
        corners_in_box = [ (c[0] - bbox[0], c[1] - bbox[1]) for c in corners ]
        print(f'{corners_in_box=}')
        self.mapbox_corners = corners_in_box
        with open(corners_file, 'w') as f:
            json.dump(corners_in_box, f, indent = 4)

        if DELETE_INTERMEDIATES:
            full_file.unlink()



    def process_rest_area(self, rest_bbox):
        #imgcat(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
        if self.file_dir.joinpath('notes.jpg').exists():
            print('notes file exists.. skipiing rest area processing')
            return

        full_img = self.get_full_img()
        img = crop_img(full_img, rest_bbox)
        h, w = img.shape[:2]
    
        def save_bbox(suffix, bbox):
            file = self.file_dir.joinpath(f'{suffix}.jpg')
            b_img = crop_img(img, bbox)
            print(f'{suffix} - {bbox}')
            if SHOW_IMG:
                imgcat(Image.fromarray(cv2.cvtColor(b_img, cv2.COLOR_BGR2RGB)))
            cv2.imwrite(str(file), b_img)
    
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        img_mask = get_color_mask(img_hsv, 'black')
    
    
        # find the easily visible square compilation box
        contours, _ = cv2.findContours(
            img_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        #show_contours(img_mask, contours)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        def is_wide(c):
            b = cv2.boundingRect(c)
            bw, bh = b[2], b[3]
            return bw/bh > 2
        contours = [ c for c in contours if not is_wide(c) ]
        c_box_bbox = cv2.boundingRect(contours[0])
        save_bbox('cbox', c_box_bbox)
    
        # things to the right of the compilation box is the compilation text
        c_box_y1 = c_box_bbox[1]
        c_box_y2 = c_box_y1 + c_box_bbox[3]
        c_text_bbox = (c_box_bbox[0] + c_box_bbox[2] + 1, c_box_bbox[1], 
                       w - c_box_bbox[0] - c_box_bbox[2] - 1, c_box_bbox[3])
        save_bbox('ctext', c_text_bbox)
    

        # just above the compilation box is the compilation header
        # and above it is the notes section
        min_gap_ratio = 25.0/2470.0
        min_gap = int(min_gap_ratio * w)
        print(f'{min_gap=}, {w=}')
    
    
        c_header_ratio = 50.0/2470.0
        c_header_len = int(c_header_ratio * w)
        print(f'{c_header_len=}, {w=}')
    
        h_proj = get_projection(img_mask, axis=1)
        print_proj(h_proj)
        breaks = get_breaks(h_proj, self.sb_break_min_val)
        #print(f'{breaks=}')
        break_index = -1
        for bi, br in enumerate(breaks):
            if br[1] > c_box_y2:
                break_index = bi
                break
    
        if break_index == -1:
            raise Exception('unable to find the notes break')
        print(f'{break_index=}')
    
        notes_cut_y = breaks[break_index - 1][0] - c_header_len
        notes_bbox = (0, 0, w, notes_cut_y)
        save_bbox('notes', notes_bbox)
    

        # the break after the compilation box is for the projection info
        # the one after that is the magnetic variation data
        #remaining_breaks = breaks[break_index:]
        #remaining_breaks = [ br for br in remaining_breaks if br[1] - br[0] > min_gap ] 
    
        #mag_var_cut_y1 = remaining_breaks[1][1]
        #mag_var_cut_y2 = remaining_breaks[2][0]
        #mag_var_bbox = (0, mag_var_cut_y1,
        #                w, mag_var_cut_y2 - mag_var_cut_y1)
        #save_bbox('magvar', mag_var_bbox)


    def process_legend_area(self, lbbox):
        file = self.file_dir.joinpath('legend.jpg')
        if file.exists():
            return
        full_img = self.get_full_img()
        img = crop_img(full_img, lbbox)
        h, w = img.shape[:2]
        if SHOW_IMG:
            imgcat(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
        cv2.imwrite(str(file), img)


    def split_image(self):
        print('splitting shrunk image')
        main_splits = self.get_shrunk_splits()

        print('processing legend area')
        self.process_legend_area(main_splits['legend'])
        print('processing sidebar rest area')
        self.process_rest_area(main_splits['rest'])
        print('processing map area to locate corners')
        self.process_map_area(main_splits['map'], main_splits['map_poly_points'])


    def get_index_geom(self):
        sheet_no = Path(self.filename).name.replace('.pdf', '').replace('_', '/')
        full_index = get_full_index()
        geom = full_index[sheet_no]
        #round_off(geom)
        return geom

    def get_source_crs(self):
        if self.src_crs is not None:
            return src_crs
        esri_wkt = Path('data/raw/OSM_SHEET_INDEX/OSM_SHEET_INDEX.prj').read_text()
        self.src_crs = CRS.from_wkt(esri_wkt, morph_from_esri_dialect=True)
        return self.src_crs

    def get_corners(self):
        if self.mapbox_corners is not None:
            return self.mapbox_corners
        corners_file = self.file_dir.joinpath('corners.json')
        with open(corners_file, 'r') as f:
            corners = json.load(f)

        self.mapbox_corners = corners
        return corners

    def create_cutline(self, ibox, file):
        sub_geoms = []
        with open(file, 'w') as f:
            cutline_data = {
                "type": "FeatureCollection",
                "name": "CUTLINE",
                "features": [{
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [ibox]
                    }
                }]
            }
            json.dump(cutline_data, f, indent=4)


    def export_internal(self, filename, out_filename, jpeg_export_quality):
        if Path(out_filename).exists():
            print(f'{out_filename} exists.. skipping export')
            return
        creation_opts = f'-co TILED=YES -co COMPRESS=JPEG -co JPEG_QUALITY={jpeg_export_quality} -co PHOTOMETRIC=YCBCR' 
        mask_options = '--config GDAL_TIFF_INTERNAL_MASK YES  -b 1 -b 2 -b 3 -mask 4'
        perf_options = '--config GDAL_CACHEMAX 512'
        cmd = f'gdal_translate {perf_options} {mask_options} {creation_opts} {filename} {out_filename}'
        run_external(cmd)


    def export(self):
        filename = str(self.file_dir.joinpath('final.tif'))
        sheet_no = self.file_dir.name
        out_filename = f'export/gtiffs/{sheet_no}.tif'
        self.export_internal(filename, out_filename, self.jpeg_export_quality)
        if self.extents is None:
            return
        for k in self.extents.keys():
            if k == 'full' or k == sheet_no:
                continue
            k_dir = Path(f'data/inter/{k}/')
            k_final_file = k_dir.joinpath('final.tif') 
            k_out_filename = f'export/gtiffs/{k}.tif'
            jpeg_export_quality = self.jpeg_export_quality
            if k in self.extra_ancillary and 'jpeg_export_quality' in self.extra_ancillary[k]:
                jpeg_export_quality = self.extra_ancillary[k]['jpeg_export_quality']

            self.export_internal(str(k_final_file), k_out_filename, jpeg_export_quality)


    def warp_mapbox(self):
        cutline_file = self.file_dir.joinpath('cutline.geojson')
        georef_file = self.file_dir.joinpath('georef.tif')
        final_file = self.file_dir.joinpath('final.tif')
        if final_file.exists():
            print(f'{final_file} exists.. skipping')
            return

        geom = self.get_index_geom()

        sheet_ibox = geom['coordinates'][0]

        def warp_file(box, cline_file, f_file):
            img_quality_config = {
                'COMPRESS': 'JPEG',
                #'PHOTOMETRIC': 'YCBCR',
                'JPEG_QUALITY': '75'
            }

            #if not USE_4326:
            #    box = [ transformer.transform(*c) for c in box ]

            self.create_cutline(box, cline_file)
            cutline_options = f'-cutline {str(cline_file)} -crop_to_cutline --config GDALWARP_IGNORE_BAD_CUTLINE YES -wo CUTLINE_ALL_TOUCHED=TRUE'

            warp_quality_config = img_quality_config.copy()
            warp_quality_config.update({'TILED': 'YES'})
            warp_quality_options = ' '.join([ f'-co {k}={v}' for k,v in warp_quality_config.items() ])
            reproj_options = f'-tps -tr 1 1 -r bilinear -t_srs "EPSG:3857"' 
            #nodata_options = '-dstnodata 0'
            nodata_options = '-dstalpha'
            perf_options = '-multi -wo NUM_THREADS=ALL_CPUS --config GDAL_CACHEMAX 1024 -wm 1024' 
            warp_cmd = f'gdalwarp -overwrite {perf_options} {nodata_options} {reproj_options} {warp_quality_options} {cutline_options} {str(georef_file)} {str(f_file)}'
            run_external(warp_cmd)

            
            #addo_quality_options = ' '.join([ f'--config {k}_OVERVIEW {v}' for k,v in img_quality_config.items() ])
            #addo_cmd = f'export GDAL_NUM_THREADS=ALL_CPUS; gdaladdo {addo_quality_options} -r average {str(final_file)} 2 4 8 16 32'
            #run_external(addo_cmd)

        sheet_no = Path(self.filename).name.replace('.pdf', '')
        if self.extents is None:
            warp_file(sheet_ibox, cutline_file, final_file)
        else:
            if sheet_no not in self.extents:
                warp_file(sheet_ibox, cutline_file, final_file)
            for k in self.extents.keys():
                if k == 'full':
                    continue
                k_dir = Path(f'data/inter/{k}/')
                k_dir.mkdir(parents=True, exist_ok=True)
                k_cutline_file = k_dir.joinpath('cutline.geojson')
                k_final_file = k_dir.joinpath('final.tif') 
                k_ibox = self.extents[k]
                warp_file(k_ibox, k_cutline_file, k_final_file) 
                # TODO: this didn't work
                # an attempt to fill partial tiffs
                #fill_tif(k, k_dir)

        # delete the georef file as it can get too big
        georef_file.unlink()

    def georeference_mapbox(self):
        #mapbox_file = self.file_dir.joinpath('mapbox.jpg')
        nogrid_file = self.file_dir.joinpath('nogrid.jpg')
        georef_file = self.file_dir.joinpath('georef.tif')
        final_file = self.file_dir.joinpath('final.tif')
        if georef_file.exists() or final_file.exists():
            print(f'{georef_file} or {final_file} exists.. skipping')
            return
        geom = self.get_index_geom()

        sheet_ibox = geom['coordinates'][0]
        if self.extents is None:
            ibox = sheet_ibox
        else:
            ibox = self.extents['full']

        corners = self.get_corners()

        src_crs = CRS.from_epsg(4326)
        # get source crs using the center of the box
        if not USE_4326:
            ibox_poly = Polygon(ibox)
            src_crs = get_utm_crs(*ibox_poly.centroid.coords[0])
            box_crs = CRS.from_epsg(4326)
            transformer = Transformer.from_crs(box_crs, src_crs, always_xy=True)
            ibox = [ transformer.transform(*c) for c in ibox ]

        if len(ibox) - 1 != len(corners):
            raise Exception(f'{len(ibox) - 1=} != {len(corners)=}')

        gcp_str = ''
        for idx, c in enumerate(corners):
            i = ibox[idx]
            gcp_str += f' -gcp {c[0]} {c[1]} {i[0]} {i[1]}'
        perf_options = '--config GDAL_CACHEMAX 128 --config GDAL_NUM_THREADS ALL_CPUS'
        translate_cmd = f'gdal_translate {perf_options} {gcp_str} -a_srs "EPSG:{src_crs.to_epsg()}" -of GTiff {str(nogrid_file)} {str(georef_file)}' 
        run_external(translate_cmd)

        if DELETE_INTERMEDIATES:
            nogrid_file.unlink()


    def remove_line(self, line, map_img):
        h, w = map_img.shape[:2]

        line_buf_ratio = 6.0 / 12980.0
        blur_buf_ratio = 30.0 / 12980.0
        blur_kern_ratio = 19.0 / 12980.0

        line_buf = round(line_buf_ratio * w)
        blur_buf = round(blur_buf_ratio * w)
        blur_kern = round(blur_kern_ratio * w)
        if blur_kern % 2 == 0:
            blur_kern += 1

        limits = Polygon([(w,0), (w,h), (0,h), (0,0), (w,0)])

        ls = LineString(line)
        line_poly = ls.buffer(line_buf, resolution=1, cap_style=CAP_STYLE.flat).intersection(limits)
        blur_poly = ls.buffer(blur_buf, resolution=1, cap_style=CAP_STYLE.flat).intersection(limits)
        bb = blur_poly.bounds
        bb = [ round(x) for x in bb ]
        # restrict to a small img strip to make things less costly
        img_strip = map_img[bb[1]:bb[3], bb[0]:bb[2]]
        sh, sw = img_strip.shape[:2]
        #cv2.imwrite('temp.jpg', img_strip)

        line_poly_t = translate(line_poly, xoff=-bb[0], yoff=-bb[1])
        mask = np.zeros(img_strip.shape[:2], dtype=np.uint8)
        poly_coords = np.array([ [int(x[0]), int(x[1])] for x in line_poly_t.exterior.coords ])
        cv2.fillPoly(mask, pts=[poly_coords], color=1)

        #img_blurred = cv2.medianBlur(img_strip, blur_kern)
        pad = int(blur_kern/2)
        img_strip_padded = cv2.copyMakeBorder(img_strip, pad, pad, pad, pad, cv2.BORDER_REFLECT_101)

        img_blurred_padded = cv2.medianBlur(img_strip_padded, blur_kern)
        img_blurred = img_blurred_padded[pad:pad+sh, pad:pad+sw]
        #cv2.imwrite('temp.jpg', img_blurred)

        img_strip[mask == 1] = img_blurred[mask == 1]


    def locate_grid_lines_by_split(self):
        corners = self.get_corners()
        c_lt, c_lb, c_rb, c_rt = corners
        v_points_t = split_line(c_lt, c_rt)
        v_points_b = split_line(c_lb, c_rb)
        h_points_l = split_line(c_lt, c_lb)
        h_points_r = split_line(c_rt, c_rb)
        v_lines = list(zip(v_points_t, v_points_b))
        h_lines = list(zip(h_points_l, h_points_r))
        return v_lines, h_lines

    def locate_grid_lines_using_coords(self):
        map_img = self.get_map_img()
        corners = self.get_corners()
        geom = self.get_index_geom()

        sheet_ibox = geom['coordinates'][0]
        if self.extents is None:
            ibox = sheet_ibox
        else:
            ibox = self.extents['full']

        if len(ibox) - 1 != len(corners):
            raise Exception(f'{len(ibox) - 1=} != {len(corners)=}')

        gcps = []
        i_hs = []
        i_vs = []
        for idx, c in enumerate(corners):
            i = ibox[idx]
            i_hs.append(i[0])
            i_vs.append(i[1])
            print(f'{c=}, {i=}')
            gcp = GroundControlPoint(row=c[1], col=c[0], x=i[0], y=i[1])
            gcps.append(gcp)
        transformer = from_gcps(gcps)

        def get_slots(p_s):
            p_s = set(p_s)
            p_s_min = min(list(p_s))
            p_s_max = max(list(p_s))
            msl_p_min = round(p_s_min) - 1
            msl_p_max = round(p_s_max) + 1
            grid_p_count = abs(msl_p_max - msl_p_min)*24
            print(f'{grid_p_count=}')
            grid_p_s = [round(msl_p_min + (1.0 / 24.0)*idx, 7) for idx in range(0, grid_p_count)]
            grid_p_s = [ g for g in grid_p_s if g >= p_s_min and g <= p_s_max ]
            grid_p_s = set(grid_p_s)
            for p in p_s:
                if p not in grid_p_s:
                    grid_p_s.add(p)
            return sorted(list(grid_p_s))
            

        grid_hs = get_slots(i_hs)
        grid_vs = get_slots(i_vs)
        print(f'{grid_hs=}')
        print(f'{grid_vs=}')
        grid_v_min = grid_vs[0]
        grid_v_max = grid_vs[-1]
        grid_h_min = grid_hs[0]
        grid_h_max = grid_hs[-1]

        v_g_lines = [ [[grid_h_min, v], [grid_h_max, v]] for v in grid_vs ] 
        h_g_lines = [ [[h, grid_v_min], [h, grid_v_max]] for h in grid_hs ]
        print(f'{v_g_lines=}')
        print(f'{h_g_lines=}')

        def transform_point(p):
            rs, cs = rowcol(transformer, [p[0]], [p[1]])
            return [cs[0], rs[0]]

        v_lines = [ [transform_point(l[0]), transform_point(l[1])] for l in v_g_lines ]
        h_lines = [ [transform_point(l[0]), transform_point(l[1])] for l in h_g_lines ]

        return v_lines, h_lines


    def remove_lines(self):
        #TODO: should take into account extents
        nogrid_file = self.file_dir.joinpath('nogrid.jpg')
        mapbox_file = self.file_dir.joinpath('mapbox.jpg')
        if nogrid_file.exists():
            print(f'{nogrid_file} file exists.. skipping')
            return

        if self.grid_lines is not None:
            v_lines, h_lines = self.grid_lines
        else:
            v_lines, h_lines = self.locate_grid_lines_using_coords()
        print(f'{v_lines=}')
        print(f'{h_lines=}')

        map_img = self.get_map_img()
        print('dropping vertical lines')
        for line in v_lines:
            self.remove_line(line, map_img)
        print('dropping horizontal lines')
        for line in h_lines:
            self.remove_line(line, map_img)

        cv2.imwrite(str(nogrid_file), map_img)
        if DELETE_INTERMEDIATES:
            mapbox_file.unlink()

    def rotate(self):
        rotated_info_file = self.file_dir.joinpath('rotated_info.txt')
        if rotated_info_file.exists():
            print('already rotated.. skipping rotation')
            return
        map_bbox, map_min_rect, _ = self.get_maparea()
        print(map_min_rect)
        _, _, angle = map_min_rect
        if angle > 45:
            angle = angle - 90

        if abs(angle) < self.auto_rotate_thresh:
            rotated_info_file.write_text(f'{angle}, not_rotated')
            return

        img = self.get_full_img()
        print(f'rotating image by {angle}')
        img_rotated = imutils.rotate_bound(img, -angle)
        rotated_file = self.file_dir.joinpath('full.rotated.jpg')
        cv2.imwrite(str(rotated_file), img_rotated)
        shutil.move(str(rotated_file), str(self.get_full_img_file()))
        rotated_info_file.write_text(f'{angle}, rotated')
        self.file_dir.joinpath('small.jpg').unlink()
        self.small_img = None
        self.full_img = None

        
    def run(self):
        final_file = self.file_dir.joinpath('final.tif')
        if final_file.exists():
            print(f'{final_file} exists.. skipping')
            return
        
        print(f'converting {filename}')
        self.convert()
        self.rotate()
        print(f'splitting {filename}')
        self.split_image()
        self.remove_lines()
        print('georeferencing image')
        self.georeference_mapbox()
        self.warp_mapbox()
        self.export()
        #self.process_legend()
        #self.process_magvar()
        #self.process_cbox()
        #self.process_notes()

    def close(self):
        if self.file_fp is not None:
            self.file_fp.close()
            self.file_fp = None



# file has no legend or any lines.. 
# locate the corners manually and join in at the nogrid stage
def handle_65A_11(filename):
    converter = Converter(filename, {}, {})
    converter.convert()
    final_file = converter.file_dir.joinpath('final.tif')
    if final_file.exists():
        print(f'{final_file} exists.. skipping')
        return

    img = converter.get_full_img()
    h, w = img.shape[:2]
    print(f'{w=}, {h=}')
    # located manually
    c_rt = [ w - 1756, 2046 ]
    c_rb = [ w - 1774, h - 2885 ]
    c_lb = [ 3815, h - 2911 ]
    c_lt = [ 3851, 2020 ]
    corners = c_lt, c_lb, c_rb, c_rt

    corners_contour = np.array(corners).reshape((-1,1,2)).astype(np.int32)
    bbox = cv2.boundingRect(corners_contour)
    print(f'{bbox=}')
    nogrid_img = crop_img(img, bbox)
    nogrid_file = converter.file_dir.joinpath('nogrid.jpg')
    full_file = converter.file_dir.joinpath('full.jpg')
    corners_file = converter.file_dir.joinpath('corners.json')
    cv2.imwrite(str(nogrid_file), nogrid_img)
    corners_in_box = [ (c[0] - bbox[0], c[1] - bbox[1]) for c in corners ]
    print(f'{corners_in_box=}')
    converter.mapbox_corners = corners_in_box
    with open(corners_file, 'w') as f:
        json.dump(corners_in_box, f, indent = 4)
    #full_file.unlink()

    converter.georeference_mapbox()
    converter.warp_mapbox()
    converter.export()
    converter.close()

def handle_55J_16(filename):
    converter = Converter(filename, {}, {})
    final_file = converter.file_dir.joinpath('final.tif')
    if final_file.exists():
        print(f'{final_file} exists.. skipping')
        return
    converter.convert(20000)
    x = int((4300.0/18000.0) * 20000)
    y = int((1039.0/18000.0) * 20000)
    w = int((7700.0/18000.0) * 20000)
    bbox = [x, y, w, w]
    full_img = converter.get_full_img()
    cropped_img = crop_img(full_img, bbox)
    cropped_file = converter.file_dir.joinpath('cropped.jpg')
    cv2.imwrite(str(cropped_file), cropped_img)
    shutil.move(str(cropped_file), str(converter.get_full_img_file()))
    converter.full_img = None
    converter.run()

super_special_handlers = {
    'data/raw/65A_11.pdf': [ handle_65A_11 ],
    'data/raw/55J_16.pdf': [ handle_55J_16 ]
}


def only_convert(filename, extra, extra_ancillary):
    print(f'processing {filename}')
    converter = Converter(filename, extra, extra_ancillary)
    mapbox_file = converter.file_dir.joinpath('mapbox.jpg')
    nogrid_file = converter.file_dir.joinpath('nogrid.jpg')
    final_file =  converter.file_dir.joinpath('final.tif')
    #if mapbox_file.exists() or nogrid_file.exists() or final_file.exists():
    #    print('downstream files exist.. not attempting conversion')
    #    return
    converter.convert()
    #converter.rotate()
    #converter.split_image()
    #converter.remove_lines()
    #converter.georeference_mapbox()
    converter.close()

def setup_fonts_folder():
    if Path('data/SOI_FONTS').exists():
        return
    fonts_zip = Path('data/raw/SOI_FONTS.zip')
    if not fonts_zip.exists():
        raise Exception(f'{fonts_zip} missing')

    print('Extracting SOI FONTS')
    with zipfile.ZipFile(str(fonts_zip), 'r') as zip_ref:
        zip_ref.extractall('data/')



def get_extra(special_cases, filename):
    extra = special_cases.get(filename, {})
    sheet_no = Path(filename).name.replace('.pdf', '')
    extents = extra.get('extents', {})
    extra_ancillary = {}
    for k in extents.keys():
        if k == 'full' or k == sheet_no:
            continue
        full_filename = f'data/raw/{k}.pdf'
        if full_filename in special_cases:
            extra_ancillary[k] = special_cases[full_filename]
    return extra, extra_ancillary


if __name__ == '__main__':
    freeze_support()

    setup_fonts_folder()

    FROM_LIST = os.environ.get('FROM_LIST', '')
    ignore_filenames = []

    #cat data/goa.txt | xargs -I {} gsutil -m cp gs://soi_data/raw/{} data/raw/
    if FROM_LIST != '':
        file_list_filename = FROM_LIST
        file_list = Path(file_list_filename).read_text().split('\n')
        file_list = [ f.strip() for f in file_list ]
        file_list = [ f for f in file_list if f != '' ]
        filenames = file_list
    else:
        filenames = glob.glob('data/raw/*.pdf')
        errors_file = Path('data/errors.txt')
        ignore_filenames = []
        if errors_file.exists():
            efnames = errors_file.read_text().split('\n')
            efnames = [ f.strip() for f in efnames ]
            ignore_filenames = [ f for f in efnames if f != '' ]


    special_cases_file = Path(__file__).parent.joinpath('special_cases.json')
    if special_cases_file.exists():
        with open(special_cases_file, 'r') as f:
            special_cases = json.load(f)
    else:
        special_cases = {}


    ONLY_CONVERT = os.environ.get('ONLY_CONVERT', '0') == '1'
    if ONLY_CONVERT:
        fut_map = {}
        with ProcessPoolExecutor(max_workers=6) as executor:
            for filename in filenames:
                if filename in known_problems:
                    continue
                if filename in super_special_handlers:
                    continue
                extra, extra_ancillary = get_extra(special_cases, filename)
                fut = executor.submit(only_convert, filename, extra, extra_ancillary)
                fut_map[fut] = filename
        
            total_count = len(fut_map.keys())
            done = 0
            for fut in as_completed(fut_map, timeout=None):
                filename = fut_map[fut]
                done += 1
                print(f'done with file: {filename} {done}/{total_count}')
                try:
                    fut.result()
                except Exception as ex:
                    print(f'got exception - {ex}')
                    ignore_filenames.append(filename)
                    error_txt = '\n'.join(ignore_filenames)
                    Path(errors_file).write_text(error_txt)
        exit(0)
    
    
    for i, filename in enumerate(filenames):
        if filename in known_problems:
            continue
        if filename in ignore_filenames:
            continue
        if filename in super_special_handlers:
            print(f'found super special handler for {filename}')
            handler = super_special_handlers[filename]
            handler, args = handler[0], handler[1:]
            handler(filename, *args)
            continue
        print(f'processing {filename} {i+1}/{len(filenames)}')
        extra, extra_ancillary = get_extra(special_cases, filename)
        print(extra)
        converter = Converter(filename, extra, extra_ancillary)
        #crs = converter.get_source_crs()
        #print(crs)
        try:
            converter.run()
            converter.close()
        except Exception as ex:
            print(f'ERROR: exception {ex} while handling {filename}')
            if FROM_LIST != '':
                raise
            ignore_filenames.append(filename)
            error_txt = '\n'.join(ignore_filenames)
            Path(errors_file).write_text(error_txt)
            
    

