import os
import os.path
import csv
import logging
import collections
import requests
import threading

from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from timeit import default_timer as timer
from humanize import naturalsize


from .captcha_helper import CaptchaHelper

logger = logging.getLogger(__name__)

BASE_URL = 'https://lgdirectory.gov.in'
INCORRECT_CAPTCHA_MESSAGE = 'The CAPTCHA image code was entered incorrectly.'


class Params:
    def __init__(self):
        self.print_captchas = False
        self.save_failed_html = False
        self.save_all_captchas = False
        self.save_failed_captchas = False
        self.base_raw_dir = 'data/raw'
        self.no_verify_ssl = False
        self.progress_bar = False
        self.connect_timeout = 10
        self.read_timeout = 60
        self.http_retries = 3

    def request_args(self):
        return {
            'verify': not self.no_verify_ssl,
            'timeout': (self.connect_timeout, self.read_timeout)
        }



class Context:
    def __init__(self):
        self.last_captcha = None
        self.csrf_token = None
        #self.base_headers = None
        self.script_session_id = ''
        self.script_batch_id = 0
        self.session = None


def get_tqdm_position():
    name = threading.currentThread().getName()
    thread_idx_str = name.replace('ThreadPoolExecutor-0_','')
    thread_idx = 0
    try:
        thread_idx = int(thread_idx_str)
    except:
        pass
    logging.info('got thread index: {}'.format(thread_idx))
    return thread_idx + 1


def get_date_str(date=None):
    if date is None:
        date = datetime.today()
    date_str = date.strftime("%d%b%Y")
    return date_str


def get_csrf_token(params, ctx):
    global BASE_URL
    logger.info('retrieving csrf token')
    web_data = ctx.session.get(BASE_URL, **params.request_args())
    if not web_data.ok:
        raise ValueError('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))
    
    page_html = web_data.text
    
    soup = BeautifulSoup(page_html, 'html.parser')
    lgd_features_section = soup.find('section', { "id" : "lgdfeatures" })
    link_fragments = lgd_features_section.find_all('a')
    link_url = None
    for link_fragment in link_fragments:
        if link_fragment.text.strip() == 'Download Directory':
            link_url = link_fragment.attrs['href']
    if link_url is None:
        raise Exception('Download directory link not found')
    csrf_token = link_url.split('?')[1].replace('OWASP_CSRFTOKEN=', '')
    return csrf_token


def get_context(params):
    ctx = Context()
    s = requests.session()
    s.mount('http://', HTTPAdapter(max_retries=params.http_retries))
    s.mount('https://', HTTPAdapter(max_retries=params.http_retries))
    ctx.session = s
    ctx.csrf_token = get_csrf_token(params, ctx)
    return ctx
 

class BaseDownloader:
    downloader_cache = {}
    def __init__(self,
                 name='',
                 desc='',
                 section='',
                 dropdown='',
                 csv_filename='',
                 full_filename=None,
                 deps=[],
                 transform=lambda x: x,
                 params=Params(),
                 ctx=Context(),
                 **kwargs):
        self.name = name
        self.desc = desc
        self.section = section
        self.dropdown = dropdown
        self.csv_filename = csv_filename
        self.full_filename = full_filename
        self.deps = deps
        self.transform = transform
        self.params = params
        self.base_url = BASE_URL
        self.captcha_helper = CaptchaHelper(params, ctx, BASE_URL)
        self.set_context(ctx)
        self.req_time = None
        self.req_size = None
        if name in BaseDownloader.downloader_cache:
            raise ValueError(f'a downloader with {name} was already instantiated')
        BaseDownloader.downloader_cache[name] = self

    def get_downloader(name):
        if name not in BaseDownloader.downloader_cache:
            raise KeyError(f'{name} not in downloader cache')
        return BaseDownloader.downloader_cache[name]

    def records_from_downloader(name):
        downloader = BaseDownloader.get_downloader(name)
        if not downloader.is_done():
            raise NotReadyException()
        csv_filename = downloader.get_filename()
        #TODO: storage handler code goes here
        with open(csv_filename) as f:
            reader = csv.DictReader(f, delimiter=';')
            for r in reader:
                yield r

    def clear_cache():
        BaseDownloader.downloader_cache.clear()

    def set_context(self, ctx):
        self.ctx = ctx
        self.captcha_helper.ctx = ctx

    def get_filename(self):
        if self.full_filename is not None:
            return self.full_filename
        path = Path(self.params.base_raw_dir).joinpath(get_date_str(), self.csv_filename)
        return str(path)

    def get_child_downloaders(self):
        return []

    def get_records(self):
        raise NotImplementedError()

    def cleanup(self):
        pass
        
    def download(self, ctx=None):
        if self.is_done():
            return

        if ctx is not None:
            self.set_context(ctx)

        # TODO: use yield in get_records and iterate to reduce memory usage?
        # TODO: if doing this.. make sure no intermediate files are left in case of request failure
        records = self.get_records()

        records_transformed = []
        for r in records:
            t = self.transform(r)
            if t != False:
                records_transformed.append(t)

        csv_filename = self.get_filename()
        dirname = os.path.dirname(csv_filename)
        if dirname != '':
            os.makedirs(dirname, exist_ok=True)

        #TODO: storage handler code goes here
        logger.info(f'writing file {csv_filename}')
        wr = None
        with open(csv_filename, 'w') as f:
            for r in records_transformed:
                if wr is None:
                    wr = csv.DictWriter(f, fieldnames=r.keys(), delimiter=';')
                    wr.writeheader()
                wr.writerow(r)

        self.cleanup()


    def is_done(self):
        filename = self.get_filename()
        return os.path.exists(filename)


    def post_with_progress(self, *args, **kwargs):
        req_args = self.params.request_args() | kwargs

        logger.info('making remote request')
        logger.debug('post data: {}'.format(kwargs.get('data', {})))
        logger.debug('post headers: {}'.format(kwargs.get('headers', {})))
        if not self.params.progress_bar:
            start = timer()
            resp = self.ctx.session.post(*args, **req_args)
            time_taken = timer() - start
            self.req_time = time_taken
            self.req_size = len(resp.content)
            logger.info('done with remote request in {:.2f} secs, size {}'.format(self.req_time, naturalsize(self.req_size)))
            return resp
        # Streaming, so we can iterate over the response.
        req_args['stream'] = True
        all_data = b''
        response = self.ctx.session.post(*args, **req_args)
        total_size_in_bytes= int(response.headers.get('content-length', 0))
        block_size = 1024 #1 Kibibyte
        with logging_redirect_tqdm():
            progress_bar = tqdm(total=total_size_in_bytes,
                                unit='iB',
                                unit_scale=True,
                                desc=self.csv_filename,
                                position=get_tqdm_position())
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                all_data += data
            progress_bar.close()
        response._content = all_data
        logger.info('done with remote request')
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            raise Exception(f"Expected content length({total_size_in_bytes}) not same as content downloaded({progress_bar.n})")
        return response



DownloaderItem = collections.namedtuple('DownloaderItem', ['downloader', 'record'])

class NotReadyException(Exception):
    pass

class MultiDownloader(BaseDownloader):
    def __init__(self, enrichers={}, delete_intermediates=True, **kwargs):
        super().__init__(**kwargs)
        self.downloader_items = None
        self.enrichers = enrichers
        self.delete_intermediates = delete_intermediates


    def populate_downloaders(self):
        raise NotImplementedError()


    def combine_records(self):
        all_records = []
        for ditem in self.downloader_items:
            #TODO: storage handler code goes here
            with open(ditem.downloader.get_filename(), 'r') as ifile:
                reader = csv.DictReader(ifile, delimiter=';')
                for r in reader:
                    for nkey, okey in self.enrichers.items():
                        r[nkey] = ditem.record[okey]
                    all_records.append(r)
        return all_records


    def get_child_downloaders(self):
        if self.is_done():
            return []
        self.populate_downloaders()
        return [x.downloader for x in self.downloader_items if not x.downloader.is_done()]


    def cleanup(self):
        if not self.delete_intermediates:
            return
        #TODO: storage handler code goes here
        for ditem in self.downloader_items:
            os.remove(ditem.downloader.get_filename())


    def get_records(self):
        self.populate_downloaders()
        for ditem in self.downloader_items:
            ditem.downloader.download(self.ctx)
        return self.combine_records()


