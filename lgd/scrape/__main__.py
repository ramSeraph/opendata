import copy
import glob
import logging
import subprocess


from datetime import datetime
from pathlib import Path
from humanize import naturalsize
from enum import Enum
from pprint import pprint
from zipfile import ZipFile, ZIP_LZMA
from concurrent.futures import (wait, FIRST_COMPLETED,
                                Future, ProcessPoolExecutor,
                                ThreadPoolExecutor)
from concurrent.futures.process import BrokenProcessPool
from google.api_core.exceptions import NotFound
try:
    from graphlib import TopologicalSorter
except ImportError:
    from graphlib_backport import TopologicalSorter

from .base import (Params, Context, expand_comps_to_run,
                   get_date_str, get_gcs_upload_args,
                   get_blobname_from_filename,
                   NotReadyException, initialize_process,
                   download_task, setup_logging)
from .captcha_helper import CaptchaHelper
from . import get_all_downloaders

logger = logging.getLogger(__name__)

#TODO: 2) add smoother killing support
#TODO: 3) cleanup logging


class Mode(Enum):
    COMPS = 'Get list of all components'
    DEPS = 'Get dependencies between components'
    STATUS = 'Status of individual comps'
    CLEANUP = 'Cleanup leftover files'
    RUN = 'Download all things'
    BEAM_RUN = 'Download all things using Apache Beam'


#TODO: handle cancellation?
class Joiner:
    def __init__(self, fut, all_comps, downloader):
        self.fut = fut
        self.pending_comps = all_comps
        self.child_map = {}
        self.downloader = downloader
        self.has_errors = False
        self.fatal_error = False

    def get_checker(self, comp):
        def done_cb(fut):
            try:
                fut.result()
            except (Exception, BrokenProcessPool) as ex:
                self.has_errors = True
                if isinstance(ex, BrokenProcessPool):
                    self.fatal_error = True
                else:
                    logger.exception('sub_call failed for comp: {}'.format(comp))

            self.pending_comps.remove(comp)
            if len(self.pending_comps) == 0:
                if self.has_errors:
                    self.fut.set_exception(Exception('Task has errors'))
                    return
                try:
                    download_task(self.downloader)
                except Exception as ex:
                    self.fut.set_result(ex)
                self.fut.set_result(None)
        return done_cb

 
   
def run_on_threads(graph, dmap, num_parallel, use_procs, params):
    ts = TopologicalSorter(graph)
    ts.prepare()
    fut_to_comp = {}
    comps_in_error = set()
    comps_done = set()
    has_changes = True
    if use_procs:
        executor = ProcessPoolExecutor(max_workers=num_parallel,
                                       initializer=initialize_process,
                                       initargs=(params, logger.getEffectiveLevel())) 
    else:
        executor = ThreadPoolExecutor(max_workers=num_parallel)

    with executor:
        # evaluate downloaders in topological sort order
        while ts.is_active():
            if not has_changes:
                #TODO: check this logic
                logger.error('No progress made. stopping')
                break
            has_changes = False
            for comp in ts.get_ready():
                downloader = dmap[comp]
                if downloader.is_done():
                    childs = []
                else:
                    childs = downloader.get_child_downloaders()
                    childs = [x for x in childs if not x.is_done()]
                if len(childs) != 0:
                    fut = Future()
                    fut.set_running_or_notify_cancel()
                    joiner = Joiner(fut, set([x.name for x in childs]), downloader)
                    for child in childs:
                        child_fut = executor.submit(download_task, child)
                        done_cb = joiner.get_checker(child.name)
                        child_fut.add_done_callback(done_cb)
                else:
                    fut = executor.submit(download_task, downloader)
                fut_to_comp[fut] = comp


            done, not_done = wait(fut_to_comp, return_when=FIRST_COMPLETED)
            for fut in done:
                has_changes = True
                has_errors = False
                fatal_error = False
                comp = fut_to_comp[fut]
                try:
                    fut.result()
                except (Exception, BrokenProcessPool) as ex:
                    if isinstance(ex, BrokenProcessPool):
                        fatal_error = True
                    else:
                        logger.exception('comp {} failed'.format(comp))
                    has_errors = True

                del fut_to_comp[fut]
                if not has_errors:
                    ts.done(comp)
                    comps_done.add(comp)
                else:
                    comps_in_error.add(comp)

            if fatal_error:
                logger.error('Broken Pool encountered.. closing task pool')
                break

    return comps_done, comps_in_error


def delete_raw_data(ctx):
    logger.info('Cleaning up raw data')
    params = ctx.params
    dir_to_delete = Path(params.base_raw_dir).joinpath(get_date_str())
    if dir_to_delete.exists():
        files_to_delete = glob.glob('{}/*'.format(str(dir_to_delete)))
        logger.info('deleting files: {}'.format(files_to_delete))
        for filename in files_to_delete:
            Path(filename).unlink()

        Path(dir_to_delete).rmdir()

    if params.enable_gcs:
        try:
            bucket = ctx.gcs_client.get_bucket(params.gcs_bucket_name)
        except NotFound:
            return

        prefix_b = get_blobname_from_filename(str(dir_to_delete) + '/', params)
        blobs_to_delete = bucket.list_blobs(prefix=prefix_b)
        if len(blobs_to_delete):
            blob_names_to_delete = set([ b.name for b in blobs_to_delete ])
            logger.info('deleting blobs: {}'.format(blob_names_to_delete))
            with ctx.gcs_client.batch():
                for blob in blobs_to_delete:
                    blob.delete()


def get_version_text():
    cmd = 'git describe --tags --dirty --always'
    (status, output) = subprocess.getstatusoutput(cmd)
    if status != 0:
        return 'unknown'
    return output


def get_license_txt():
    date = datetime.today()
    date_year = date.strftime("%Y")
    date_ddmm = date.strftime("%d%m")
    license_txt = f"""
    Government Open Data License – India
    
    Copyright (c) Ministry of Panchayati Raj, {date_year}, Local Government Directory, {date_ddmm}, https://lgdirectory.gov.in/
    
    Terms and Conditions of Use of Data
    
    a . Attribution: The user must acknowledge the provider, source, and license of data by explicitly publishing the attribution statement11, including the DOI (Digital Object Identifier), or the URL (Uniform Resource Locator), or the URI (Uniform Resource Identifier) of the data concerned.
    
    b . Attribution of Multiple Data: If the user is using multiple data together and/or listing of sources of multiple data is not possible, the user
    may provide a link to a separate page/list that includes the attribution statements and specific URL/URI of all data used.
    
    c . Non-endorsement: The user must not indicate or suggest in any manner that the data provider(s) endorses their use and/or the user.
    
    d . No Warranty: The data provider(s) are not liable for any errors or omissions, and will not under any circumstances be liable for any direct, indirect, special, incidental, consequential, or other loss, injury or damage caused by its use or otherwise arising in connection with this license or the data, even if specifically advised of the possibility of such loss, injury or damage. Under any circumstances, the user may not hold the data provider(s) responsible for: i) any error, omission or loss of data, and/or ii) any undesirable consequences due to the use of the data as part of an application/product/service (including violation of any prevalent law).
    
    e . Continuity of Provision: The data provider(s) will strive for continuously updating the data concerned, as new data regarding the same becomes available. However, the data provider(s) do not guarantee the continued supply of updated or up-to-date versions of the data, and will not be held liable in case the continued supply of updated data is not provided.
    
    https://data.gov.in/government-open-data-license-india
    """
    return license_txt

def archive_all_data(downloaders):
    logger.info('archiving all data')
    if len(downloaders) == 0:
        logger.error('downloader list provided for archiving is empty')
        return False

    ctx = downloaders[0].ctx
    params = ctx.params
    filenames = [ x.get_filename() for x in downloaders ]
    base_raw_dir = params.base_raw_dir

    date_str = get_date_str()
    zip_filename = f'{base_raw_dir}/{date_str}.zip'

    if params.enable_gcs:
        blob_name = get_blobname_from_filename(zip_filename, params)
        bucket_name = params.gcs_archive_bucket_name
        try:
            bucket = ctx.gcs_client.get_bucket(bucket_name)
        except NotFound:
            logger.info(f'Creating bucket {bucket_name}')
            bucket = ctx.gcs_client.create_bucket(bucket_name, location='ASIA-SOUTH1')
            bucket.make_public(future=True)

        blob = bucket.blob(blob_name)
        if blob.exists():
            logger.info(f'blob {blob_name} already exists, shortcircuiting..')
            return True

    if Path(zip_filename).exists():
        if not params.enable_gcs:
            logger.info(f'{zip_filename} already exists, shortcircuiting..')
            return True
    else:
        missing = []
        for filename in filenames:
            path = Path(filename)
            if not path.exists():
                missing.append(filename)
        if len(missing):
            logger.error(f'missing files for archiving: {missing}')
            return False

        data_license_file = str(Path(params.base_raw_dir).joinpath(get_date_str(), 'DATA_LICENSE'))
        with open(data_license_file, 'w') as f:
            f.write(get_license_txt())
        code_version_file = str(Path(params.base_raw_dir).joinpath(get_date_str(), 'CODE_VERSION'))
        with open(code_version_file, 'w') as f:
            f.write(get_version_text())


        filenames.append(data_license_file)
        filenames.append(code_version_file)

        logger.info(f'Creating zipfile {zip_filename} for archiving')
        with ZipFile(zip_filename, 'w', ZIP_LZMA) as zip_obj:
            for filename in filenames:
                path = Path(filename)
                arcname = '/{}/{}'.format(date_str, path.name)
                zip_obj.write(filename, arcname)
        logger.info('Done creating zipfile for archiving')


    if not params.enable_gcs:
        return True

    zip_filesize = naturalsize(Path(zip_filename).stat().st_size)
    logger.info(f'uploading blob {blob_name}, size: {zip_filesize}')
    blob.upload_from_filename(filename=zip_filename, **get_gcs_upload_args(params))
    return True


def run(params, mode, comps_to_run=set(), comps_to_not_run=set(), num_parallel=1, use_procs=False):
    ctx = Context(params)
    all_downloaders = get_all_downloaders(ctx)
    dmap = {d.name:d for d in all_downloaders}
    graph = {d.name:d.deps for d in all_downloaders}

    if mode != Mode.COMPS or mode != Mode.DEPS:
        all_comp_names = set([d.name for d in all_downloaders])
        if len(comps_to_not_run) == 0:
            if len(comps_to_run) == 0:
                comps_to_run = all_comp_names
            unknown_comps = comps_to_run - all_comp_names
            if len(unknown_comps) != 0:
                raise Exception('Unknown components specified: {}'.format(unknown_comps))
        else:
            unknown_comps = comps_to_not_run - all_comp_names
            if len(unknown_comps) != 0:
                raise Exception('Unknown components specified: {}'.format(unknown_comps))
            comps_to_run = all_comp_names - comps_to_not_run

        comps_to_run_expanded = expand_comps_to_run(comps_to_run, graph)
        if len(comps_to_not_run):
            overriden = comps_to_run_expanded.intersection(comps_to_not_run)
            if len(overriden):
                logger.warning(f'comps {overriden} going to run despite exclusion')
 

    if mode == Mode.COMPS:
        return {d.name:{'desc': d.desc,
                        'filename': d.csv_filename,
                        'lgd_location': '{} --> {}'.format(d.section, d.dropdown)} for d in all_downloaders}
    if mode == Mode.DEPS:
        return graph

    if mode == Mode.STATUS:
        status = {}
        for d in all_downloaders:
            if d.name not in comps_to_run_expanded:
                continue
            logger.debug('getting status for {}'.format(d.name))
            if d.is_done():
                status[d.name] = 'COMPLETE'
            else:
                try:
                    childs = d.get_child_downloaders()
                    status[d.name] = {}
                    for c in childs:
                        status[d.name][c.name] = 'COMPLETE' if c.is_done() else 'INCOMPLETE'
                except NotReadyException:
                    childs = []

                if len(childs) == 0:
                    status[d.name] = 'INCOMPLETE'
        return status


    if mode == Mode.CLEANUP:
        for downloader in all_downloaders:
            if downloader.name not in comps_to_run_expanded:
                continue
            try:
                childs = downloader.get_child_downloaders()
            except NotReadyException:
                childs = []

            if len(childs) and downloader.is_done():
                downloader.cleanup()

        return { 'cleanup': True } 


    if mode == Mode.RUN or mode == Mode.BEAM_RUN:
        # pull all the captcha related model files
        CaptchaHelper.prepare(params.captcha_model_dir)

        logger.info(f'going to run comps: {comps_to_run_expanded}')
        graph_to_run = {d.name:d.deps for d in all_downloaders if d.name in comps_to_run_expanded}

        if mode == Mode.RUN:
            comps_done, comps_in_error = run_on_threads(graph_to_run, dmap, num_parallel, use_procs, params)
        else:
            from .beam_helper import run_on_beam
            comps_done, comps_in_error = run_on_beam(comps_to_run_expanded, params, num_parallel)

        result = { 'done': comps_done, 'error': comps_in_error, 'left': comps_to_run_expanded - (comps_done | comps_in_error) }
        if params.archive_data:
            success = archive_all_data(all_downloaders)
            log_level = logging.INFO if success else logging.ERROR
            log_msg = 'archiving {}'.format('successful' if success else 'failed')
            logger.log(log_level, log_msg)
            if success:
                delete_raw_data(ctx)

            result['archival_status'] = success
        return result



if __name__ == '__main__':
    import argparse

    class SmartFormatter(argparse.ArgumentDefaultsHelpFormatter):
        def _split_lines(self, text, width):
            if text.startswith('R|'):
                return text[2:].splitlines()  
            # this is the RawTextHelpFormatter._split_lines
            return argparse.ArgumentDefaultsHelpFormatter._split_lines(self, text, width)

    default_params = Params()
    default_params_dict = copy.copy(vars(default_params))
    default_params_dict['log_level'] = 'INFO'
    default_params_dict['mode'] = Mode.RUN
    default_params_dict['comp'] = []
    default_params_dict['no_comp'] = []
    default_params_dict['parallel'] = 1

    mode_choices = Mode.__members__.keys()
    mode_help_strs = [ '{}: {}'.format(k, Mode[k].value) for k in Mode.__members__.keys() ]
    parser = argparse.ArgumentParser(formatter_class=SmartFormatter)
    parser.add_argument('-m', '--mode', help='R|mode to run script in,\n\t' + '\n\t'.join(mode_help_strs), choices=mode_choices, type=str)

    parser.add_argument('-c', '--comp', help='R|component to select, no choice implies all\nget list of components by running this script with COMPS mode argument', action='extend', nargs='+', type=str)
    parser.add_argument('-N', '--no-comp', help='R|component to deselect\nget list of components by running this script with COMPS mode argument', action='extend', nargs='+', type=str)


    parser.add_argument('-R', '--read-timeout', help='http read timeout in secs', type=int)
    parser.add_argument('-C', '--connect-timeout', help='http connect timeout in secs', type=int)
    parser.add_argument('--no-verify-ssl', help='don\'t verify ssl for connections', action='store_true')
    parser.add_argument('-r', '--http-retries', help='number of times to retry on http failure', type=int)
    parser.add_argument('--progress-bar', help='show progress bar', action='store_true')

    parser.add_argument('--print-captchas', help='print captchas on failure', action='store_true')
    parser.add_argument('--save-failed-html', help='save html for failed requests', action='store_true')
    parser.add_argument('--save-all-captchas', help='save all captchas encountered', action='store_true')
    parser.add_argument('--save-failed-captchas', help='save all captchas which we failed for', action='store_true')

    parser.add_argument('-p', '--parallel', help='number of parallel downloads', type=int)
    parser.add_argument('--use-procs', help='use multiple processes for parllel downloads', action='store_true')
    parser.add_argument('--base-raw-dir', help='directory to write data to, will be created if it doesn\'t exist', type=str)
    parser.add_argument('--temp-dir', help='directory to write temp data to, will be created if it doesn\'t exist', type=str)
    parser.add_argument('--captcha-model-dir', help='location of the directory with tesseract models', type=str)
    parser.add_argument('--archive-data', help='archive data into a zip file and delete the staging files', action='store_true')

    parser.add_argument('--enable-gcs', help='R|enable writing to gcs, base-raw-dir is used as staging area for the data,\n' +
                                             ' credentials need to be made available through the GOOGLE_APPLICATION_CREDENTIALS env variable', action='store_true')
    parser.add_argument('--gcs-bucket-name', help='which bucket to write raw data to in gcs', type=str)
    parser.add_argument('--gcs-archive-bucket-name', help='which bucket to write archived data to in gcs', type=str)
    parser.add_argument('--gcs-upload-timeout', help='timeout in secs for upload to gcs', type=float)
    parser.add_argument('--gcs-upload-retry-deadline', help='max deadline in secs for upload to gcs', type=float)
    parser.add_argument('--gcs-upload-retry-initial', help='initial delay in secs for retrying upload to gcs', type=float)
    parser.add_argument('--gcs-upload-retry-maximum', help='maximum delay in secs for retrying upload to gcs', type=float)
    parser.add_argument('--gcs-upload-retry-multiplier', help='multiplier to increase delay between various retries to upload to gcs', type=float)

    parser.add_argument('-l', '--log-level', help='Set the logging level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], type=str)
    parser.set_defaults(**default_params_dict)

    args, leftover = parser.parse_known_args()
    log_level = args.log_level
    comps_to_run = args.comp
    comps_to_not_run = args.no_comp
    num_parallel = args.parallel
    use_procs = args.use_procs

    if len(comps_to_run) and len(comps_to_not_run):
        raise Exception("Can't specify bot comps to tun and not run")

    setup_logging(log_level)

    mode = Mode[args.mode]
    if leftover:
        msg = 'unrecognized arguments: {}'.format(' '.join(leftover))
        if mode == Mode.BEAM_RUN:
            logger.warning(msg)
        else:
            parser.error(msg)

    args_dict = vars(args)
    logger.debug(f'Running with args: {args_dict}')

    del args_dict['log_level']
    del args_dict['comp']
    del args_dict['mode']
    del args_dict['parallel']
    del args_dict['use_procs']

    params = Params()
    params.__dict__ = args_dict

    ret = run(params, mode, set(comps_to_run), set(comps_to_not_run), num_parallel, use_procs)
    pprint(ret)
    if mode == Mode.RUN and params.archive_data and not ret['archival_status']:
        exit(1)
