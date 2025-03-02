# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "numpy",
#     "requests",
#     "opencv-python-headless",
#     "pdfminer-six",
#     "pillow",
#     "pypdf",
#     "scipy",
# ]
# ///

import re
import time
import json
import shutil
import subprocess
from pathlib import Path

import cv2

from pdfminer.image import ImageWriter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTImage
from pdfminer.pdftypes import resolve_all, PDFObjRef, PDFNotImplementedError

from pypdf import PdfReader
import PIL
import requests
import numpy as np
from scipy import interpolate

PIL.Image.MAX_IMAGE_PIXELS = None

inter_dir = Path('data/inter')

download_dir = Path('data/raw')
export_dir = Path('export/compressed/')

def get_file_dir(filename):
    file_p = Path(filename)
    sheet_no = file_p.name.replace('.pdf', '')
    dir_p = inter_dir / sheet_no
    dir_p.mkdir(parents=True, exist_ok=True)
    return dir_p

'''
unknown keyword: '664.933.8752.6782'
warning: ignoring zlib error: incorrect data check
page data/raw/45A_7.pdf 1
warning: ... repeated 2 times...
'''

def is_expected_error(err_txt):
    lines = err_txt.split('\n')
    lines = [ li.strip() for li in lines if li.strip() != '' ]
    patterns = [
        r"error:\s+unknown keyword:\s+'[^']+'",
        r"warning:\s+ignoring zlib error:\s+incorrect data check",
        r"page\s+data/raw/[A-Z0-9_]+\.pdf\s+1",
        r"warning:\s+[\.]+\s+repeated\s+\d+\s+times\s*[\.]+",
    ]
    for line in lines:
        matched = False
        for p in patterns:
            if re.search(p, line):
                matched = True
                break
        if not matched:
            return False
    return True

def run_external(cmd, expected_error_fn=None):
    print(f'running cmd - {cmd}')
    start = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    print(f'STDOUT: {res.stdout}')
    print(f'STDERR: {res.stderr}')
    print(f'command took {end - start} secs to run')
    if res.returncode != 0:
        if expected_error_fn is not None and expected_error_fn(res.stderr):
            return
        raise Exception(f'command {cmd} failed with exit code: {res.returncode}')

def get_dpi(file):
    dpi_file = Path('dpi.txt')
    if dpi_file.exists():
        dpi_file.unlink()
    run_external(f"identify -units PixelsPerInch -format '%x\\n' {file} > {dpi_file}")
    dpi = int(dpi_file.read_text().strip())
    dpi_file.unlink()
    return dpi

def get_images(layout):
    imgs = []
    if isinstance(layout, LTImage):
        imgs.append(layout)

    objs = getattr(layout, '_objs', [])
    for obj in objs:
        imgs.extend(get_images(obj))
    return imgs


MAX_SIZE = 10 * 1024 * 1024
def predict_quality_for_size(known_qualities, known_sizes, target_size):
    known_qualities = np.array(known_qualities)
    known_sizes = np.array(known_sizes)
    
    # Sort by size to ensure monotonicity (important for interpolation)
    idx = np.argsort(known_sizes)
    known_sizes = known_sizes[idx]
    known_qualities = known_qualities[idx]

    if len(known_sizes) == 1:
        target_quality = (known_qualities[0] *  target_size) / known_sizes[0]
        return target_quality

    kind = 'cubic'
    if len(known_qualities) == 2:
        kind = 'linear'
    elif len(known_qualities) == 3:
        kind = 'quadratic'

    interpolator = interpolate.interp1d(
        known_sizes, known_qualities, 
        kind=kind, 
        bounds_error=False,
        fill_value='extrapolate'
    )
    predicted_quality = float(interpolator(target_size))
    return predicted_quality


class Converter:
    def __init__(self, filename, extra={}, extra_ancillary={}):
        self.filename = filename
        self.file_fp = None
        self.file_dir = get_file_dir(filename)
        self.cur_step = None
        self.full_img = None
        self.flavor = None
        self.pdf_document = None
        self.src_crs = None
        self.extra_ancillary = extra_ancillary
        self.pdf_rotate = extra.get('pdf_rotate', 0)
        self.jpeg_export_quality = extra.get('jpeg_export_quality', 10)

    def get_pdf_doc(self):
        self.file_fp = open(self.filename, "rb")
        parser = PDFParser(self.file_fp)
        document = PDFDocument(parser)
        return document


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
            #print(image)
            #print(image.colorspace)

            # fix to pdfminer bug
            if len(image.colorspace) == 1 and isinstance(image.colorspace[0], PDFObjRef):
                image.colorspace = resolve_all(image.colorspace[0])
                if not isinstance(image.colorspace, list):
                    image.colorspace = [ image.colorspace ]

            #print(image.colorspace)
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


    def convert_pdf_to_image(self):
        inp = PdfReader(open(self.filename, 'rb'))
        page = inp.pages[0]
        print(f'Advertised ROTATE: {page.rotation}')
        rotate = self.pdf_rotate
        print(f'ROTATE: {rotate}')
        img_filename = str(self.get_full_img_file())
        print('converting pdf to image using mupdf')
        run_external(f'bin/mutool draw -n data/SOI_FONTS -r 300 -c rgb -o {img_filename} {self.filename}', expected_error_fn=is_expected_error)
        if rotate == 90 or rotate == 270:
            print('rotating image')
            img = cv2.imread(img_filename)
            img_rotate = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE if rotate == 90 else cv2.ROTATE_90_COUNTERCLOCKWISE)
            rotate_filename = img_filename.replace('.jpg', '.rotated.jpg')
            cv2.imwrite(rotate_filename, img_rotate)
            shutil.move(rotate_filename, img_filename)



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
        elif 'GS PDF LIB' in doc_producer:
            flavor = 'GSPDF'
        elif 'Adobe PDF Library' in doc_producer:
            flavor = 'Microstation'
        elif 'ImageMill Imaging Library' in doc_producer:
            flavor = 'ImageMill'
        else:
            print(document.info)
            raise Exception('Unknown flavor')
 
        flav_file.write_text(flavor)
        self.flavor = flavor
        return flavor

    def get_full_img_file(self):
        return Path(self.file_dir).joinpath('full.jpg')

    def get_compressed_file(self):
        return Path(self.file_dir).joinpath('compressed.jpg')


    def convert(self):
        img_file = self.get_full_img_file()
        if img_file.exists():
            print(f'file {img_file} exists.. skipping extraction')
            return
    
        flavor = self.get_flavor()
        if flavor in ['Image PDF', 'Photoshop']:
            self.image_pdf_extract()
        else:
            self.convert_pdf_to_image()

    def fix_dpi(self):
        img_file = self.get_full_img_file()
        dpi = get_dpi(img_file)
        if dpi != 300:
            temp_file = Path('temp.jpg')
            if temp_file.exists():
                temp_file.unlink()
            run_external(f'magick -units PixelsPerInch {img_file} -density 300 {temp_file}')
            shutil.move(temp_file, img_file)


    def compress(self):
        img_file = self.get_full_img_file()
        compressed_file = self.get_compressed_file()
        if compressed_file.exists():
            print(f'file {compressed_file} exists.. skipping compression')
            return

        temp_file = Path('temp.jpg')
        shutil.copy(img_file, compressed_file)
        quality = 100
        known_qualities = [ quality ]
        known_sizes = []
        prev_size = None
        while True:
            curr_size = compressed_file.stat().st_size
            known_sizes.append(curr_size)
            
            if curr_size < MAX_SIZE:
                break

            if prev_size is not None and curr_size > prev_size:
                known_sizes = [curr_size]
                known_qualities = [ known_qualities[-1] ]
            prev_size = curr_size

            quality = predict_quality_for_size(known_qualities, known_sizes, MAX_SIZE)
            quality = int(quality)
            if quality < 10:
                print(f'{quality=} less than 10.. skipping') 
                break
            run_external(f'bin/cjpeg -outfile {temp_file} -quality {quality} -baseline {compressed_file}')
            shutil.copy(temp_file, compressed_file)
            known_qualities.append(quality)
            #if prev_quality > quality:
            #    break
            #prev_quality = quality

    def close(self):
        if self.file_fp is not None:
            self.file_fp.close()
            self.file_fp = None

    def run(self):
        sheet_no = Path(filename).name.replace('.pdf', '')
        export_file = export_dir / f'{sheet_no}.jpg'
        if export_file.exists():
            return
        print(f'converting {sheet}')
        converter.convert()
        print(f'fixing dpi for {sheet}')
        converter.fix_dpi()
        print(f'compressing {sheet}')
        converter.compress()
        compressed_file = self.get_compressed_file()
        shutil.copy(compressed_file, export_file)

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

def add_to_done(p):
    with open('done.txt', 'a') as f:
        f.write(p)
        f.write('\n')

def get_done_list():
    done_file = Path('done.txt')
    if not done_file.exists():
        return set()
    lines = done_file.read_text().split('\n')
    lines = [ li.strip() for li in lines ]
    lines = [ li for li in lines if li != '' ]
    return set(lines)

def get_pdfs():
    lines = Path('listing_pdfs.txt').read_text().split('\n')
    pdfs = [ line.strip('\n').split(' ')[1] for line in lines if line.strip('\n') != '']
    pdfs = [ p for p in pdfs if not p.endswith('.unavailable') ]
    return pdfs


def download_from_github(p):
    out_file = download_dir / f'{p}.pdf'
    if out_file.exists():
        return out_file
    resp = requests.get(f'https://github.com/ramSeraph/opendata/releases/download/soi-pdfs/{p}.pdf')
    if not resp.ok:
        raise Exception(f'unable to download {p}')
    
    out_file.write_bytes(resp.content)
    return out_file



if __name__ == '__main__':
    import sys
    from_list_file = Path(sys.argv[1])

    from_list = from_list_file.read_text().split('\n')
    from_list = [ f.strip() for f in from_list if f.strip() != '' ]
    total = len(from_list)
    
    special_cases = {}
    special_cases_file = Path(__file__).parent.joinpath('special_cases.json')
    if special_cases_file.exists():
        special_cases = json.loads(special_cases_file.read_text())

    export_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for sheet in from_list:
        count += 1
        filename = f'data/raw/{sheet}.pdf'
        print(f'handling {sheet=} {count}/{total}')
        extra, extra_ancillary = get_extra(special_cases, filename)
        converter = Converter(filename, extra, extra_ancillary)
        converter.run()
        converter.close()

