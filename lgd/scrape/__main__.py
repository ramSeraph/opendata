import time
import copy
import logging


from enum import Enum
from pprint import pprint
from graphlib import TopologicalSorter
from threading import local
from concurrent.futures import (wait, FIRST_COMPLETED, ALL_COMPLETED,
                                Future, ThreadPoolExecutor)

from .base import Params, Context, get_context
from . import get_all_downloaders

logger = logging.getLogger(__name__)

#TODO: 2) add smoother killing support
#TODO: 3) cleanup logging


class Mode(Enum):
    COMPS = 'Get list of all components'
    DEPS = 'Get dependencies between components'
    RUN = 'Download all things'

local_data = local()

def download(downloader):
    logger.info('getting {}'.format(downloader.desc))
    if getattr(local_data, 'ctx', None) is None:
        local_data.ctx = get_context(downloader.params)
    downloader.download(local_data.ctx)


#TODO: handle cancellation?
class Joiner:
    def __init__(self, fut, all_comps, downloader):
        self.fut = fut
        self.pending_comps = all_comps
        self.child_map = {}
        self.downloader = downloader
        self.has_errors = False

    def get_checker(self, comp):
        def done_cb(fut):
            try:
                fut.result()
            except Exception:
                self.has_errors = True
                logger.exception('sub_call failed for comp: {}'.format(comp))

            self.pending_comps.remove(comp)
            if len(self.pending_comps) == 0:
                if self.has_errors:
                    self.fut.set_exception(Exception('Task has errors'))
                    return
                try:
                    download(self.downloader)
                except Exception as ex:
                    self.fut.set_result(ex)
                self.fut.set_result(None)
        return done_cb

 
def set_context(params):
    local_data.ctx = get_context(params)
    # try to get all threads to run this by delaying completion
    time.sleep(1)

   
def prime_thread_contexts(params, executor):
    ctx_futs = []
    for i in range(num_parallel):
        fut = executor.submit(set_context, params)
        ctx_futs.append(fut)
    done, not_done = wait(ctx_futs, return_when=ALL_COMPLETED)
    for fut in done:
        if fut.exception() is not None:
            logger.error('encountered exception while setting context')
            raise fut.exception()


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


def run(params, mode, comps_to_run=set(), comps_to_not_run=set(), num_parallel=1):
    all_downloaders = get_all_downloaders(params, Context())
    if mode == Mode.COMPS:
        return {d.name:{'desc': d.desc,
                        'filename': d.csv_filename,
                        'lgd_location': '{} --> {}'.format(d.section, d.dropdown)} for d in all_downloaders}
    if mode == Mode.DEPS:
        return {d.name:d.deps for d in all_downloaders}

    if mode == Mode.RUN:
        dmap = {d.name:d for d in all_downloaders}
        graph = {d.name:d.deps for d in all_downloaders}

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
        

        logger.info(f'going to run comps: {comps_to_run_expanded}')
        graph_to_run = {d.name:d.deps for d in all_downloaders if d.name in comps_to_run_expanded}

        ts = TopologicalSorter(graph_to_run)
        ts.prepare()
        fut_to_comp = {}
        comps_in_transit = set()
        comps_in_error = set()
        comps_done = set()
        has_changes = True
        with ThreadPoolExecutor(max_workers=num_parallel) as executor:
            # prime the threads with seperate contexts
            prime_thread_contexts(params, executor)
  
            # evaluate downloaders in topological sort order
            while ts.is_active():
                if not has_changes:
                    #TODO: check this logic
                    logger.error('No progress made. stopping')
                    break
                has_changes = False
                for comp in ts.get_ready():
                    if comp in comps_in_transit or comp in comps_in_error:
                        continue
                    downloader = dmap[comp]
                    childs = downloader.get_child_downloaders()
                    if len(childs) != 0:
                        fut = Future()
                        fut.set_running_or_notify_cancel()
                        joiner = Joiner(fut, set([x.name for x in childs]), downloader)
                        for child in childs:
                            child_fut = executor.submit(download, child)
                            done_cb = joiner.get_checker(child.name)
                            child_fut.add_done_callback(done_cb)
                    else:
                        fut = executor.submit(download, downloader)
                    fut_to_comp[fut] = comp
                    comps_in_transit.add(comp)


                done, not_done = wait(fut_to_comp, return_when=FIRST_COMPLETED)
                for fut in done:
                    has_changes = True
                    has_errors = False
                    comp = fut_to_comp[fut]
                    try:
                        fut.result()
                    except Exception:
                        logger.exception('comp {} failed'.format(comp))
                        has_errors = True

                    del fut_to_comp[fut]
                    comps_in_transit.remove(comp)
                    if not has_errors:
                        ts.done(comp)
                        comps_done.add(comp)
                    else:
                        comps_in_error.add(comp)

        return { 'done': comps_done, 'error': comps_in_error, 'left': comps_to_run_expanded - (comps_done | comps_in_error) }


if __name__ == '__main__':
    import argparse
    from colorlog import ColoredFormatter

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
    parser.add_argument('-s', '--no-verify-ssl', help='don\'t verify ssl for connections', action='store_true')
    parser.add_argument('-r', '--http-retries', help='number of times to retry on http failure', type=int)
    parser.add_argument('-b', '--progress-bar', help='show progress bar', action='store_true')

    parser.add_argument('-P', '--print-captchas', help='print captchas on failure', action='store_true')
    parser.add_argument('-H', '--save-failed-html', help='save html for failed requests', action='store_true')
    parser.add_argument('-A', '--save-all-captchas', help='save all captchas encountered',action='store_true')
    parser.add_argument('-F', '--save-failed-captchas', help='save all captchas which we failed for', action='store_true')

    parser.add_argument('-p', '--parallel', help='number of parallel downloads', type=int)
    parser.add_argument('-D', '--base-raw-dir', help='directory to write data to, will be created if it doesn\'t exist', type=str)
    parser.add_argument('-l', '--log-level', help='Set the logging level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], type=str)
    parser.set_defaults(**default_params_dict)

    args = parser.parse_args()
    log_level = args.log_level
    comps_to_run = args.comp
    comps_to_not_run = args.no_comp
    mode = Mode[args.mode]
    num_parallel = args.parallel

    if len(comps_to_run) and len(comps_to_not_run):
        raise Exception("Can't specify bot comps to tun and not run")

    formatter = ColoredFormatter("%(log_color)s%(asctime)s [%(levelname)+8s][%(threadName)s] %(message)s",
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

    args_dict = vars(args)
    logger.info(f'Running with args: {args_dict}')

    del args_dict['log_level']
    del args_dict['comp']
    del args_dict['mode']
    del args_dict['parallel']

    params = Params()
    params.__dict__ = args_dict

    ret = run(params, mode, set(comps_to_run), set(comps_to_not_run), num_parallel)
    pprint(ret)
