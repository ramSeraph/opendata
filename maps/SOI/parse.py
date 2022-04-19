import shutil
import json
import glob
import time
import subprocess
from pathlib import Path

import cv2
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
    threshold = cv2.dilate(threshold, el)
    dmask = cv2.dilate(threshold, el, iterations=iterations)

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
            lower = np.array([140,74,76])
            upper = np.array([166,255,255])
        elif color == 'black':
            lower = np.array([0, 0, 0])
            upper = np.array([179, 255, 80])
        elif color == 'grey':
            lower = np.array([0, 0, 50])
            upper = np.array([179, 10, 120])
        elif color == 'white':
            lower = np.array([0, 0, 230])
            upper = np.array([179, 6, 255])
        else:
            raise Exception(f'{color} not handled')
        img_mask = cv2.inRange(img_hsv, lower, upper)
        img_masks.append(img_mask)

    final_mask = img_masks[0]
    for img_mask in img_masks[1:]:
        orred = np.logical_or(final_mask, img_mask)
        final_mask = orred

    return final_mask


def get_ext_count(point, img_mask, ext_thresh):
    x, y = point
    h, w = img_mask.shape[:2]
    uc = 0
    uc += np.count_nonzero(img_mask[y:y+10, x])
    uc += np.count_nonzero(img_mask[y:y+10, x+1])
    uc += np.count_nonzero(img_mask[y:y+10, x-1])

    dc = 0
    dc += np.count_nonzero(img_mask[y-10:y, x])
    dc += np.count_nonzero(img_mask[y-10:y, x+1])
    dc += np.count_nonzero(img_mask[y-10:y, x-1])

    lc = 0
    lc += np.count_nonzero(img_mask[y, x:x+10])
    lc += np.count_nonzero(img_mask[y+1, x:x+10])
    lc += np.count_nonzero(img_mask[y-1, x:x+10])

    rc = 0
    rc += np.count_nonzero(img_mask[y, x-10:x])
    rc += np.count_nonzero(img_mask[y+1, x-10:x])
    rc += np.count_nonzero(img_mask[y-1, x-10:x])

    counts = [ uc, dc, rc, lc ]
    print(f'{point=}, {counts=}')
    exts = [ c > ext_thresh for c in counts ]
    return exts.count(True)
 

def get_intersection_point(img_hsv, ext_thresh):
    img_mask = get_color_mask(img_hsv, ['black', 'grey'])
    img_mask_g = img_mask.astype(np.uint8)
    h, w = img_mask.shape[:2]
    img_mask_g = img_mask_g*255
    imgcat(Image.fromarray(img_mask_g))

    v_mask, v_lines = find_lines(img_mask_g, direction='vertical', line_scale=2)
    h_mask, h_lines = find_lines(img_mask_g, direction='horizontal', line_scale=2)
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
        ips.append((c1, c2))


    #res = np.where(only_lines == 1)
    #ips = list(zip(res[1], res[0]))
    print(f'{ips=}')
    #imgcat(Image.fromarray(only_lines*255))

    for ip in ips:
        ext_count = get_ext_count(ip, img_mask, ext_thresh)
        print(f'{ip=}, {ext_count}')
        if ext_count == 4:
            return ip

    raise Exception('no intersection point found')



def locate_corners(img_hsv):
    corner_ratio = 400.0 / 9000.0
    ext_thresh_ratio = 20.0 / 18000.0

    w = img_hsv.shape[1]
    h = img_hsv.shape[0]
    cw = round(corner_ratio * w)
    ch = round(corner_ratio * h)
    y = h - 1 - ch
    x = w - 1 - cw

    # take the four corners
    corner_boxes = []
    corner_boxes.append(((0, 0), (cw, ch)))
    corner_boxes.append(((0, y), (cw, ch)))
    corner_boxes.append(((x, y), (cw, ch)))
    corner_boxes.append(((x, 0), (cw, ch)))

    # get intersection points
    points = []
    for corner_box in corner_boxes:
        bx, by = corner_box[0]
        bw, bh = corner_box[1]
        c_img = img_hsv[by:by+bh, bx:bx+bw]
        print(f'{corner_box=}')
        ipoint = get_intersection_point(c_img, ext_thresh_ratio * w)
        ipoint = bx + ipoint[0], by + ipoint[1]
        points.append(ipoint)
    return points

def show_contours(o_bimg, contours):
    b = o_bimg.copy()
    rgb = cv2.merge([b*255,b*255,b*255])
    cv2.drawContours(rgb, contours, -1, (0, 255, 0), 2, cv2.LINE_AA)
    imgcat(Image.fromarray(rgb))
    #cv2.imwrite('temp.jpg', rgb)

def get_breaks(proj):
    breaks = []
    s = None
    for i, v in enumerate(proj):
        if v != 0:
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
        raise Exception(f'command {cmd} failed')


def crop_img(img, bbox):
    x, y, w, h = bbox
    return img[y:y+h, x:x+w]


def scale_bbox(bbox, rw, rh):
    b = bbox
    return (int(b[0]*rw), int(b[1]*rh), int(b[2]*rw), int(b[3]*rh))

def translate_bbox(bbox, ox, oy):
    b = bbox
    return (b[0] + ox, b[1] + oy, b[2], b[3])


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
    

class Converter:
    def __init__(self, filename):
        self.filename = filename
        self.file_fp = None
        self.file_dir = get_file_dir(filename)
        self.cur_step = None
        self.small_img = None
        self.full_img = None
        self.flavor = None
        self.pdf_document = None
        self.mapbox_corners = None


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
            print(images[0])
            fname = img_writer.export_image(images[0])
            out_filename = str(self.get_full_img_file())
            print(f'writing {out_filename}')
            shutil.move(fname, out_filename)
            pno += 1


    def convert_pdf_to_image(self):
        print('converting pdf to image using pdftocairo')
        run_external(f'pdftocairo -singlefile -r 72 -scale-to 18000 -jpeg {self.filename}')
        exp_out_file = Path(self.filename).name.replace('.pdf', '.jpg')
        shutil.move(exp_out_file, str(self.get_full_img_file()))


    def convert(self):
        img_file = self.get_full_img_file()
        if img_file.exists():
            print(f'file {img_file} exists.. skipping conversion')
            return
    
        flavor = self.get_flavor()
        if flavor == 'Image PDF':
            self.image_pdf_extract()
        else:
            self.convert_pdf_to_image()


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
        self.small_img = small_img
        return small_img




    def get_maparea(self):
        img = self.get_shrunk_img()
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        start = time.time()
        img_mask = get_color_mask(img_hsv, 'pink') 
        print('getting pink contours for whole image')
        contours, hierarchy = cv2.findContours(
            img_mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )
        ctuples = list(zip(list(contours), list(hierarchy[0])))
        end = time.time()
        print(f'pink contours took {end - start} secs')
        show_contours(img_mask, [x[0] for x in ctuples])
        ctuples_s = sorted(ctuples, key=lambda x: cv2.contourArea(x[0]), reverse=True)
        #print(ctuples_s[0])
        map_inner_contour_idx = ctuples_s[0][1][2]
        map_contour = ctuples[map_inner_contour_idx][0]
        #map_contour = ctuples_s[0][0]
        map_bbox = cv2.boundingRect(map_contour)
        print(f'{map_bbox=}')
        map_area = map_bbox[2] * map_bbox[3]
        h, w = img.shape[:2]
        total_area = w * h
        if total_area / map_area > 3:
            show_contours(img_mask, [map_contour])
            raise Exception(f'map area less than expected, {map_area=}, {total_area=}')
    
        return map_bbox

    def split_sidebar_area(self, img):
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, w = img_hsv.shape[:2]
        img_mask = get_color_mask(img_hsv, 'pink') 
        print('getting pink contours for sidebar image')
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

        map_bbox = self.get_maparea()
 
        mb = map_bbox
        sbx, sby, sbw, sbh = (0, mb[1]-1,
                              mb[0], mb[3])
        sb_bbox = (sbx, sby, sbw, sbh)
        print(f'{sb_bbox=}')
    
        img = self.get_shrunk_img()
        sb_img = crop_img(img, sb_bbox)
        legend_bbox, rest_bbox = self.split_sidebar_area(sb_img)
        legend_bbox = translate_bbox(legend_bbox, sbx, sby)
        rest_bbox = translate_bbox(rest_bbox, sbx, sby)

        full_img = self.get_full_img()
        small_img = self.get_shrunk_img()
        fh, fw = full_img.shape[:2]
        h, w = small_img.shape[:2]
        rh, rw = float(fh)/float(h), float(fw)/float(w)

        bboxes = [ map_bbox, legend_bbox, rest_bbox ]
        full_bboxes = [ scale_bbox(bbox, rw, rh) for bbox in bboxes ]
        bbox_dict = {
            'map': full_bboxes[0],
            'legend': full_bboxes[1],
            'rest': full_bboxes[2],
        }
        with open(shrunk_splits_file, 'w') as f:
            json.dump(bbox_dict, f, indent=4)

        return bbox_dict
        

    def process_map_area(self, map_bbox):
        mapbox_file = self.file_dir.joinpath('mapbox.jpg')
        corners_file = self.file_dir.joinpath('corners.json')
        if corners_file.exists():
            print('corners file exists.. shortcircuiting')
            return

        full_img = self.get_full_img()
        full_img_hsv = cv2.cvtColor(full_img, cv2.COLOR_BGR2HSV)
        map_img_hsv = crop_img(full_img_hsv, map_bbox)
        corners = locate_corners(map_img_hsv)
        corners_contour = np.array(corners).reshape((-1,1,2)).astype(np.int32)
        bbox = cv2.boundingRect(corners_contour)
        print(f'{bbox=}')
        print(f'{corners=}')
        map_img_hsv = crop_img(map_img_hsv, bbox)
        print('writing the main mapbox file')
        cv2.imwrite(str(mapbox_file), cv2.cvtColor(map_img_hsv, cv2.COLOR_HSV2BGR))
        corners_in_box = [ (c[0] - bbox[0], c[1] - bbox[1]) for c in corners ]
        print(f'{corners_in_box=}')
        self.mapbox_corners = corners_in_box
        with open(corners_file, 'w') as f:
            json.dump(corners_in_box, f, indent = 4)



    def process_rest_area(self, rest_bbox):
        #imgcat(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
        if self.file_dir.joinpath('magvar.jpg').exists():
            print('magvar file exists.. skipiing rest area processing')
            return

        full_img = self.get_full_img()
        img = crop_img(full_img, rest_bbox)
        h, w = img.shape[:2]
    
        def save_bbox(suffix, bbox):
            file = self.file_dir.joinpath(f'{suffix}.jpg')
            b_img = crop_img(img, bbox)
            print(f'{suffix} - {bbox}')
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
        #print_proj(h_proj)
        breaks = get_breaks(h_proj)
        print(f'{breaks=}')
        break_index = -1
        for bi, br in enumerate(breaks):
            if br[1] > c_box_y2:
                break_index = bi
                break
    
        if break_index == -1:
            raise Exception('unable to find the notes break')
    
        notes_cut_y = breaks[break_index - 1][0] - c_header_len
        notes_bbox = (0, 0, w, notes_cut_y)
        save_bbox('notes', notes_bbox)
    

        # the break after the compilation box is for the projection info
        # the one after that is the magnetic variation data
        remaining_breaks = breaks[break_index:]
        remaining_breaks = [ br for br in remaining_breaks if br[1] - br[0] > min_gap ] 
    
        mag_var_cut_y1 = remaining_breaks[1][1]
        mag_var_cut_y2 = remaining_breaks[2][0]
        mag_var_bbox = (0, mag_var_cut_y1,
                        w, mag_var_cut_y2 - mag_var_cut_y1)
        save_bbox('magvar', mag_var_bbox)


    def split_image(self):
        print('splitting shrunk image')
        main_splits = self.get_shrunk_splits()

        print('processing sidebar rest area')
        self.process_rest_area(main_splits['rest'])
        print('processing map area to locate corners')
        self.process_map_area(main_splits['map'])

    def get_index_geom(self):
        sheet_no = Path(self.filename).name.replace('.pdf', '').replace('_', '/')
        full_index = get_full_index()
        geom = full_index[sheet_no]
        return geom

    def get_corners(self):
        if self.mapbox_corners is not None:
            return self.mapbox_corners
        corners_file = self.file_dir.joinpath('corners.json')
        with open(corners_file, 'r') as f:
            corners = json.load(f)

        self.mapbox_corners = corners
        return corners

    def georeference_mapbox(self):
        mapbox_file = self.file_dir.joinpath('mapbox.jpg')
        cutline_file = self.file_dir.joinpath('cutline.geojson')
        georef_file = self.file_dir.joinpath('georef.tif')
        final_file = self.file_dir.joinpath('final.tif')
        if final_file.exists():
            print(f'{final_file} exists.. skipping')
            return
        geom = self.get_index_geom()
        ibox = geom['coordinates'][0]
        i_lt, i_lb, i_rb, i_rt, _ = ibox
        corners = self.get_corners()
        c_rt, c_rb, c_lb, c_lt = corners
        gcp_str = ''
        gcp_str += f' -gcp {c_lt[0]} {c_lt[1]} {i_lt[0]} {i_lt[1]}'
        gcp_str += f' -gcp {c_lb[0]} {c_lb[1]} {i_lb[0]} {i_lb[1]}'
        gcp_str += f' -gcp {c_rb[0]} {c_rb[1]} {i_rb[0]} {i_rb[1]}'
        gcp_str += f' -gcp {c_rt[0]} {c_rt[1]} {i_rt[0]} {i_rt[1]}'
        translate_cmd = f'gdal_translate {gcp_str}  -of GTiff {str(mapbox_file)} {str(georef_file)}' 
        run_external(translate_cmd)

        img_quality_config = {
            'COMPRESS': 'JPEG',
            #'PHOTOMETRIC': 'YCBCR',
            'JPEG_QUALITY': '50'
        }

        warp_quality_config = img_quality_config.copy()
        warp_quality_config.update({'TILED': 'YES'})

        warp_quality_options = ' '.join([ f'-co {k}={v}' for k,v in warp_quality_config.items() ])

        with open(cutline_file, 'w') as f:
            cutline_data = {
                    "type": "FeatureCollection",
                    "name": "CUTLINE",
                    "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
                    "features": [{
                        "type": "Feature",
                        "properties": {},
                        "geometry": geom
                    }]
            }
            json.dump(cutline_data, f, indent=4)

        reproj_options = '-tps -tr 1 1 -r bilinear -s_srs "EPSG:4326" -t_srs "EPSG:3857"' 
        cutline_options = f'-cutline {str(cutline_file)} -crop_to_cutline'
        warp_cmd = f'gdalwarp -overwrite -multi -wo NUM_THREADS=ALL_CPUS -dstalpha {reproj_options} {warp_quality_options} {cutline_options} {str(georef_file)} {str(final_file)}'
        run_external(warp_cmd)

        
        addo_quality_options = ' '.join([ f'--config {k}_OVERVIEW {v}' for k,v in img_quality_config.items() ])
        addo_cmd = f'gdaladdo {addo_quality_options} -r average {str(final_file)} 2 4 8 16 32'
        run_external(addo_cmd)

        # delete the georef file
        georef_file.unlink()

        #TODO: remove lines somehow
        # split based on coordinates and use cblend?
        # write your own version of cblend?




    def run(self):
        print(f'converting {filename}')
        self.convert()
        print(f'splitting {filename}')
        self.split_image()
        print('georeferencing image')
        self.georeference_mapbox()

    def close(self):
        if self.file_fp is not None:
            self.file_fp.close()
            self.file_fp = None



filenames = glob.glob('data/raw/*.pdf')
#filenames = ['data/raw/57J_3.pdf']
for filename in filenames:
    print(f'processing {filename}')
    converter = Converter(filename)
    converter.run()
    converter.close()
