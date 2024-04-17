import os
import os.path
import gc
import csv
import copy
import logging
import collections
import requests
import functools

from threading import local
from datetime import datetime, timedelta
from pathlib import Path
from timeit import default_timer as timer


import psutil
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from humanize import naturalsize

from .captcha_helper import CaptchaHelper

logger = logging.getLogger(__name__)

BASE_URL = 'https://lgdirectory.gov.in'
INCORRECT_CAPTCHA_MESSAGE = 'The CAPTCHA image code was entered incorrectly.'
RUN_FOR_PREV_DAY = int(os.environ.get('RUN_FOR_PREV_DAY', '0'))


class Params:
    def __init__(self):
        self.print_captchas = False
        self.save_failed_html = False
        self.save_all_captchas = False
        self.save_failed_captchas = False
        self.captcha_model_dir = str(Path(__file__).parent.joinpath('captcha', 'models'))
        self.archive_data = False
        self.base_raw_dir = 'data/raw'
        self.temp_dir = 'data/temp'
        self.save_intermediates = False
        self.no_verify_ssl = False
        self.connect_timeout = 10
        self.read_timeout = 60
        self.http_retries = 3

    def request_args(self):
        return {
            'verify': not self.no_verify_ssl,
            'timeout': (self.connect_timeout, self.read_timeout)
        }

    def from_dict(dikt):
        params = Params()
        params.__dict__.update(dikt)
        return params



class Context:
    def __init__(self, params=Params()):
        self.params = params
        self.last_captcha = None
        self._csrf_token = None
        self._csrf_token_reports = None
        self.script_session_id = ''
        self.script_batch_id = 0
        self._session = None

    def set_csrf_tokens(self):
        global BASE_URL
        logger.info('retrieving csrf token')
        web_data = self.session.get(BASE_URL, **self.params.request_args())
        if not web_data.ok:
            raise ValueError('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))
        
        page_html = web_data.text
        
        soup = BeautifulSoup(page_html, 'html.parser')
        lgd_features_section = soup.find('section', { "id" : "hero" })
        link_fragments = lgd_features_section.find_all('a')
        link_url = None
        for link_fragment in link_fragments:
            if link_fragment.text.strip() == 'Download Directory':
                link_url = link_fragment.attrs['href']
        if link_url is None:
            raise Exception('Download directory link not found')

        self._csrf_token = link_url.split('?')[1].replace('OWASP_CSRFTOKEN=', '')

        lgd_reports_div = soup.find('div', { "id" : "reports-model" })
        links = lgd_reports_div.find_all('a')
        link_url = None
        #TODO: individual links to reports can probably be extracted
        #      exceptional reports are probably a common url with different params
        for link in links:
            link_url = link.attrs['href']
            break
        if link_url is None:
            raise Exception('No Reports link not found')

        self._csrf_token_reports = link_url.split('?')[1].replace('OWASP_CSRFTOKEN=', '')


    def set_session(self):
        s = requests.session()
        retries = self.params.http_retries
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries
        )
        s.mount('http://', HTTPAdapter(max_retries=retry))
        s.mount('https://', HTTPAdapter(max_retries=retry))
        self._session = s


    @property
    def session(self):
        if self._session is None:
            self.set_session()
        return self._session


    @property
    def csrf_token(self):
        if self._csrf_token is None:
            self.set_csrf_tokens()
        return self._csrf_token


    @property
    def csrf_token_reports(self):
        if self._csrf_token_reports is None:
            self.set_csrf_tokens()
        return self._csrf_token_reports


# moved here due to problems with module imports and python multiprocessing module

def setup_logging(log_level):
    from colorlog import ColoredFormatter
    formatter = ColoredFormatter("%(log_color)s%(asctime)s [%(levelname)-5s][%(process)d][%(threadName)s] %(message)s",
                                 datefmt='%Y-%m-%d %H:%M:%S',
	                             reset=True,
	                             log_colors={
	                             	'DEBUG':    'cyan',
	                             	'INFO':     'green',
	                             	'WARNING':  'yellow',
	                             	'ERROR':    'red',
	                             	'CRITICAL': 'red',
	                             },
	                             secondary_log_colors={},
	                             style='%')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(level=log_level, handlers=[handler])


local_data = local()

def initialize_context(params):
    local_data.ctx = Context(params)

def initialize_process(params, log_level):
    initialize_context(params)
    setup_logging(log_level)

def get_local_context(params):
    if getattr(local_data, 'ctx', None) is None:
        initialize_context(params)
    return local_data.ctx


def get_date_str(date=None):
    if date is None:
        date = datetime.today()
        if RUN_FOR_PREV_DAY:
            date = date - timedelta(days=RUN_FOR_PREV_DAY)
    date_str = date.strftime("%d%b%Y")
    return date_str


def get_blobname_from_filename(filename, params):
    blob_name = filename.replace(str(Path(params.base_raw_dir)) + '/', '')
    return blob_name


def add_defaults_to_args(defaults, args):
    args_final = {}  
    args_final.update(defaults)
    args_final.update(args)
    return args_final


def expand_children(downloaders):
    downloaders_expanded = []
    for downloader in downloaders:
        try:
            childs = downloader.get_child_downloaders()
        except NotReadyException:
            childs = []

        for child in childs:
            downloaders_expanded.append(child)
            downloader.add_dep(child.name)
        downloaders_expanded.append(downloader)
    return downloaders_expanded


def expand_comps_to_run(comps_to_run, graph):
    comps_to_run_expanded = copy.copy(comps_to_run)
    while True:
        temp_set = set()
        for comp in comps_to_run_expanded:
            temp_set.add(comp)
            deps = graph[comp]
            for dep in deps:
                temp_set.add(dep)

        if len(temp_set) == len(comps_to_run_expanded):
            break
        comps_to_run_expanded = temp_set
    return comps_to_run_expanded


def identity(r, prev_recs):
    return r

def ignore_if_empty_field(field_name, r, prev_recs):
    if r[field_name] == '':
        return False
    return r

transform_fn_map = {
    'identity': identity,
    'ignore_if_empty_field': ignore_if_empty_field,
}

def get_tranform_fn(name, *args):
    if name not in transform_fn_map:
        raise Exception(f'missing transform function {name}')
    transform_fn = functools.partial(transform_fn_map[name], *args)
    return transform_fn

def get_mem_info():
    pid = os.getpid()
    smem = psutil.virtual_memory()
    pmem = psutil.Process(pid).memory_info()
    logger.info('system full memory: {}, system used memory: {}, process used memory: {}'.format(naturalsize(smem.total), naturalsize(smem.used), naturalsize(pmem.rss))) 
    return smem, pmem

def download_task(downloader):
    logger.info('getting {}'.format(downloader.desc))
    get_mem_info()
    downloader.download(get_local_context(downloader.ctx.params))
    gc.collect()



class BaseDownloader:
    downloader_cache = {}
    comp_map = None
    def __init__(self, **kwargs):
        if BaseDownloader.comp_map is None:
            raise Exception('comp_map is not set')
        kwargs = add_defaults_to_args({'name': None,
                                       'base_name': None,
                                       'desc': None,
                                       'csv_filename': None,
                                       'transform': ['identity'],
                                       'deps': [],
                                       'ctx': Context(Params())},
                                       kwargs)

        self.name = kwargs['name']
        lookup_name = kwargs['base_name'] or kwargs['name']
        known_info = BaseDownloader.comp_map[lookup_name]

        self.desc = kwargs['desc'] or known_info['desc']
        self.csv_filename = kwargs['csv_filename'] or known_info['file']
        self.expected_fields = known_info['fields']
        self.dropdown = known_info['dropdown']

        self.transform = kwargs['transform']
        self.deps = kwargs['deps']
        self.base_url = BASE_URL
        self.captcha_helper = CaptchaHelper(kwargs['ctx'], BASE_URL)
        self.set_context(kwargs['ctx'])
        self.req_time = None
        self.req_size = None
        # TODO: do this using __new__
        #if self.name in BaseDownloader.downloader_cache:
        #    logger.warning(f'a downloader with {self.name} was already instantiated')
        BaseDownloader.downloader_cache[self.name] = self
        del kwargs['ctx']
        self.ctr_args = kwargs

    def get_kwargs(self):
        return self.ctr_args

    def add_dep(self, dep):
        if dep not in self.deps:
            self.deps.append(dep)

    @classmethod
    def set_known_site_map(cls, known_site_map):
        known_site_map = copy.copy(known_site_map)
        comp_map = {}
        for e in known_site_map:
            comp = e['comp']
            del e['comp']
            if comp == 'IGNORE':
                continue
            comp_map[comp] = e

        cls.comp_map = comp_map


    @classmethod
    def get_subclasses(cls):
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def from_dict(cls, classname, kwargs, params_dict):
        kwargs['ctx'] = Context(Params.from_dict(params_dict))
        subclass_map = {s_cls.__name__: s_cls for s_cls in cls.get_subclasses()}
        return subclass_map[classname](**kwargs)

    def get_downloader(name):
        if name not in BaseDownloader.downloader_cache:
            raise KeyError(f'{name} not in downloader cache')
        return BaseDownloader.downloader_cache[name]

    def records_from_downloader(name):
        downloader = BaseDownloader.get_downloader(name)
        return downloader.retrieve_records()

    def clear_cache():
        BaseDownloader.downloader_cache.clear()

    def set_context(self, ctx):
        self.ctx = ctx
        self.captcha_helper.ctx = ctx

    def get_filename(self):
        path = Path(self.ctx.params.base_raw_dir).joinpath(get_date_str(), self.csv_filename)
        return str(path)

    def get_blobname(self):
        csv_filename = self.get_filename()
        blob_name = get_blobname_from_filename(csv_filename, self.ctx.params)
        return blob_name

    def get_child_downloaders(self):
        return []

    def get_records(self):
        raise NotImplementedError()

    def retrieve_records(self):
        csv_filename = self.get_filename()

        if not self.is_done():
            raise NotReadyException()

        with open(csv_filename) as f:
            reader = csv.DictReader(f)
            for r in reader:
                yield r

    def cleanup(self):
        pass

    def download(self, ctx=None):
        if ctx is not None:
            self.set_context(ctx)

        if self.is_done():
            return

        if not Path(self.get_filename()).exists():
            # TODO: use yield in get_records and iterate to reduce memory usage?
            # TODO: if doing this.. make sure no intermediate files are left in case of request failure
            records = self.get_records()

            transform_fn = get_tranform_fn(*self.transform)
            records_transformed = []
            for r in records:
                t = transform_fn(r, records_transformed)
                if t != False:
                    records_transformed.append(t)

            csv_filename = self.get_filename()
            dirname = os.path.dirname(csv_filename)
            if dirname != '':
                os.makedirs(dirname, exist_ok=True)

            logger.info(f'writing file {csv_filename}')
            try:
                wr = None
                with open(csv_filename, 'w') as f:
                    for r in records_transformed:
                        if wr is None:
                            wr = csv.DictWriter(f, fieldnames=r.keys())
                            wr.writeheader()
                        wr.writerow(r)
            except KeyboardInterrupt:
                logger.warning(f'Interrupted while writing {csv_filename}, deleting incomplete file')
                Path(csv_filename).unlink(missing_ok=True)
                raise

        self.cleanup()


    def is_done(self):
        filename = self.get_filename()
        return Path(filename).exists()


    def post_with_progress(self, *args, **kwargs):
        req_args = self.ctx.params.request_args()
        req_args.update(kwargs)

        logger.info('making remote request')
        logger.debug('post data: {}'.format(kwargs.get('data', {})))
        logger.debug('post headers: {}'.format(kwargs.get('headers', {})))
        start = timer()
        resp = self.ctx.session.post(*args, **req_args)
        time_taken = timer() - start
        self.req_time = time_taken
        self.req_size = len(resp.content)
        logger.info('done with remote request in {:.2f} secs, size {}'.format(self.req_time, naturalsize(self.req_size)))
        return resp

    def get_temp_file(self, content, ext):
        temp_dir_p = Path(self.ctx.params.temp_dir)
        if not temp_dir_p.exists():
            temp_dir_p.mkdir(parents=True, exist_ok=True)

        temp_file_p = temp_dir_p.joinpath(self.name + ext)
        if temp_file_p.exists():
            temp_file_p.unlink()

        with open(temp_file_p, 'wb') as f:
            f.write(content)

        temp_file_name = str(temp_file_p)
        return temp_file_name




DownloaderItem = collections.namedtuple('DownloaderItem', ['downloader', 'record'])

class NotReadyException(Exception):
    pass

class MultiDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        kwargs = add_defaults_to_args({'enrichers': {},
                                       'delete_intermediates':True}, kwargs)
        super().__init__(**kwargs)
        self.downloader_items = None
        self.enrichers = kwargs['enrichers']
        self.delete_intermediates = kwargs['delete_intermediates']


    def populate_downloaders(self):
        raise NotImplementedError()


    def combine_records(self):
        all_records = []
        for ditem in self.downloader_items:
            records = ditem.downloader.retrieve_records()
            for r in records:
                for nkey, okey in self.enrichers.items():
                    r[nkey] = ditem.record[okey]
                all_records.append(r)
        return all_records


    def get_child_downloaders(self):
        self.populate_downloaders()
        return [x.downloader for x in self.downloader_items]


    def cleanup(self):
        if not self.delete_intermediates:
            return

        logger.info('Cleaning up for {}'.format(self.name))

        files_to_delete = []
        for ditem in self.downloader_items:
            filename = ditem.downloader.get_filename() 
            if Path(filename).exists():
                files_to_delete.append(filename)

        if len(files_to_delete):
            logger.info(f'deleting files: {files_to_delete}')
            for filename in files_to_delete:
                os.remove(filename)

    def get_records(self):
        self.populate_downloaders()
        for ditem in self.downloader_items:
            ditem.downloader.download(self.ctx)
        return self.combine_records()


