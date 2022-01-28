import os
import os.path
import gc
import csv
import copy
import logging
import collections
import requests
import functools
import resource
import psutil

from threading import local, currentThread
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from timeit import default_timer as timer
from humanize import naturalsize
from google.cloud import storage
from google.api_core.exceptions import NotFound
from google.cloud.storage.retry import DEFAULT_RETRY
from google.cloud.storage.constants import _DEFAULT_TIMEOUT




from .captcha_helper import CaptchaHelper

logger = logging.getLogger(__name__)

BASE_URL = 'https://lgdirectory.gov.in'
INCORRECT_CAPTCHA_MESSAGE = 'The CAPTCHA image code was entered incorrectly.'
RUN_FOR_PREV_DAY = 0
TRACING = 1
if TRACING:
    import tracemalloc


class Params:
    def __init__(self):
        self.print_captchas = False
        self.save_failed_html = False
        self.save_all_captchas = False
        self.save_failed_captchas = False
        self.captcha_model_dir = str(Path(__file__).parent.joinpath('captcha', 'models'))
        self.archive_data = False
        self.base_raw_dir = 'data/raw'
        self.no_verify_ssl = False
        self.progress_bar = False
        self.connect_timeout = 10
        self.read_timeout = 60
        self.http_retries = 3
        self.gcs_bucket_name = 'lgd_data_raw'
        self.gcs_archive_bucket_name = 'lgd_data_archive'
        self.enable_gcs = False
        self.gcs_upload_timeout = _DEFAULT_TIMEOUT
        self.gcs_upload_retry_deadline = DEFAULT_RETRY._deadline
        self.gcs_upload_retry_initial = DEFAULT_RETRY._initial
        self.gcs_upload_retry_maximum = DEFAULT_RETRY._maximum
        self.gcs_upload_retry_multiplier = DEFAULT_RETRY._multiplier

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
        self.script_session_id = ''
        self.script_batch_id = 0
        self._session = None
        self._gcs_client = None

    def set_csrf_token(self):
        global BASE_URL
        logger.info('retrieving csrf token')
        web_data = self.session.get(BASE_URL, **self.params.request_args())
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

        self._csrf_token = link_url.split('?')[1].replace('OWASP_CSRFTOKEN=', '')

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
            self.set_csrf_token()
        return self._csrf_token

    @property
    def gcs_client(self):
        if not self.params.enable_gcs:
            return None
        if self._gcs_client is None:
            self._gcs_client = storage.Client()
        return self._gcs_client
    

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
    if TRACING:
        tracemalloc.start()
    initialize_context(params)
    setup_logging(log_level)

def get_local_context(params):
    if getattr(local_data, 'ctx', None) is None:
        initialize_context(params)
    return local_data.ctx

class MemoryTracker():
    def __init__(self, desc):
        self.desc = desc
        self.initial_mem_usage = 0
        self.initial_snapshot = None

    def __enter__(self):
        self.initial_mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if TRACING:
            tracemalloc.reset_peak()
            self.initial_snapshot = tracemalloc.take_snapshot()
        return self

    def __exit__(self, exc_type, value, traceback):
        mem_usage_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if TRACING:
            size, peak = tracemalloc.get_traced_memory()
            size, peak = naturalsize(size), naturalsize(peak)
            logger.debug(f"[ memory size: {size}, peak: {peak} for {self.desc} ]")
            final_snapshot = tracemalloc.take_snapshot()
            top_stats = final_snapshot.compare_to(self.initial_snapshot, 'traceback')
            logger.debug(f"[ Top 20 differences for {self.desc} ]")
            for stat in top_stats[:20]:
                logger.debug(stat)
        logger.info('mem_usage increase for {}: {} kb'.format(self.desc, mem_usage_after - self.initial_mem_usage))

def get_gcs_upload_args(params):
    timeout = params.gcs_upload_timeout
    modified_retry = DEFAULT_RETRY.with_deadline(params.gcs_upload_retry_deadline)
    modified_retry = modified_retry.with_delay(initial=params.gcs_upload_retry_initial,
                                               multiplier=params.gcs_upload_retry_multiplier,
                                               maximum=params.gcs_upload_retry_maximum)
    return { 'retry': modified_retry, 'timeout': timeout }


def get_tqdm_position():
    name = currentThread().getName()
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


def download_task(downloader):
    logger.info('getting {}'.format(downloader.desc))
    pid = os.getpid()
    smem = psutil.virtual_memory()
    pmem = psutil.Process(pid).memory_info()
    logger.info('system full memory: {}, system used memory: {}, process used memory: {}'.format(naturalsize(smem.total), naturalsize(smem.used), pmem(pmem.rss))) 
    downloader.download(get_local_context(downloader.ctx.params))
    gc.collect()



class BaseDownloader:
    downloader_cache = {}
    def __init__(self, **kwargs):
        kwargs = add_defaults_to_args({'name': '',
                                       'desc': '',
                                       'section': '',
                                       'dropdown': '',
                                       'transform': ['identity'],
                                       'csv_filename': '',
                                       'deps': [],
                                       'ctx': Context(Params())},
                                       kwargs)

        self.name = kwargs['name']
        self.desc = kwargs['desc']
        self.section = kwargs['section']
        self.dropdown = kwargs['dropdown']
        self.transform = kwargs['transform']
        self.csv_filename = kwargs['csv_filename']
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

        if self.ctx.params.enable_gcs and not Path(csv_filename).exists():
            self.download_from_gcs(csv_filename, self.get_blobname())

        with open(csv_filename) as f:
            reader = csv.DictReader(f, delimiter=';')
            for r in reader:
                yield r

    def cleanup(self):
        pass

    def download_from_gcs(self, filename, blobname, ignore_not_found=False):
        try:
            bucket = self.ctx.gcs_client.get_bucket(self.ctx.params.gcs_bucket_name)
            logger.debug(f'downloading {blobname} to local file {filename}')
            dirname = os.path.dirname(filename)
            if dirname != '':
                os.makedirs(dirname, exist_ok=True)
            bucket.blob(blobname).download_to_filename(filename)
        except NotFound:
            if ignore_not_found:
                logger.warning(f'{blobname} not found in gcs.. ignoring')
                return
            raise


    def upload_to_gcs(self, filename, blob_name, force=False):
        bucket_name = self.ctx.params.gcs_bucket_name
        try:
            bucket = self.ctx.gcs_client.get_bucket(bucket_name)
        except NotFound:
            logger.info(f'Creating bucket {bucket_name}')
            bucket = self.ctx.gcs_client.create_bucket(bucket_name, location='ASIA-SOUTH1')
            bucket.make_public(future=True)

        blob = bucket.blob(blob_name)
        if blob.exists() and not force:
            logger.warning(f'blob {blob_name} already exists.. not uploading')
            return

        filesize = naturalsize(Path(filename).stat().st_size)
        logger.info(f'uploading blob {blob_name}, size: {filesize}')
        blob.upload_from_filename(filename=filename, **get_gcs_upload_args(self.ctx.params))
 
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
            wr = None
            with open(csv_filename, 'w') as f:
                for r in records_transformed:
                    if wr is None:
                        wr = csv.DictWriter(f, fieldnames=r.keys(), delimiter=';')
                        wr.writeheader()
                    wr.writerow(r)

        if self.ctx.params.enable_gcs:
            self.upload_to_gcs(self.get_filename(), self.get_blobname())
       
        self.cleanup()


    def is_done(self):
        if not self.ctx.params.enable_gcs:
            filename = self.get_filename()
            return Path(filename).exists()

        blob_name = self.get_blobname()
        try:
            bucket = self.ctx.gcs_client.get_bucket(self.ctx.params.gcs_bucket_name)
        except NotFound:
            return False
        return bucket.blob(blob_name).exists()




    def post_with_progress(self, *args, **kwargs):
        req_args = self.ctx.params.request_args()
        req_args.update(kwargs)

        logger.info('making remote request')
        logger.debug('post data: {}'.format(kwargs.get('data', {})))
        logger.debug('post headers: {}'.format(kwargs.get('headers', {})))
        if not self.ctx.params.progress_bar:
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

        if self.ctx.params.enable_gcs:
            try:
                bucket = self.ctx.gcs_client.get_bucket(self.ctx.params.gcs_bucket_name)
            except NotFound:
                bucket = None

            prefix_f = self.get_filename().replace('.csv', '_')
            prefix_b = get_blobname_from_filename(prefix_f, self.ctx.params)
            existing_child_blob_names = set([ b.name for b in bucket.list_blobs(prefix=prefix_b) ])

        files_to_delete = []
        blobs_to_delete = []
        for ditem in self.downloader_items:
            filename = ditem.downloader.get_filename() 
            if Path(filename).exists():
                files_to_delete.append(filename)

            if not self.ctx.params.enable_gcs:
                continue

            if bucket is None:
                continue
            blob_name = ditem.downloader.get_blobname()
            if blob_name in existing_child_blob_names:
                blob = bucket.blob(blob_name)
                blobs_to_delete.append(blob)

        if len(files_to_delete):
            logger.info(f'deleting files: {files_to_delete}')
            for filename in files_to_delete:
                os.remove(filename)

        if self.ctx.params.enable_gcs and len(blobs_to_delete):
            logger.info('deleting blobs: {}'.format([ b.name for b in blobs_to_delete ]))
            with self.ctx.gcs_client.batch():
                for blob in blobs_to_delete:
                    blob.delete()
        

    def get_records(self):
        self.populate_downloaders()
        for ditem in self.downloader_items:
            ditem.downloader.download(self.ctx)
        return self.combine_records()


