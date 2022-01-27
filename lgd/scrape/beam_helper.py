
import copy
import pprint
import logging
from apache_beam import (Pipeline, Create, ParDo,
                         DoFn, RestrictionProvider)
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io.iobase import RestrictionTracker, RestrictionProgress
from apache_beam.utils.timestamp import Duration
try:
    from graphlib import TopologicalSorter
except ImportError:
    from graphlib_backport import TopologicalSorter

from .base import (Params, Context, MemoryTracker,
                   BaseDownloader, expand_children,
                   expand_comps_to_run)
from . import get_all_downloaders

logger = logging.getLogger(__name__)


class CompsRange:
    def __init__(self, ready_infos, unready_infos, params_dict):
        self.ready_infos = ready_infos
        self.unready_infos = unready_infos
        self.params_dict = params_dict

    @property
    def ready_downloaders(self):
        return [ BaseDownloader.from_dict(info[0], info[1], self.params_dict) for info in self.ready_infos ]

    @property
    def unready_downloaders(self):
        return [ BaseDownloader.from_dict(info[0], info[1], self.params_dict) for info in self.unready_infos ]

    @property
    def downloaders(self):
        return self.ready_downloaders + self.unready_downloaders

    @property
    def ready_names(self):
        return [ info[1]['name'] for info in self.ready_infos ]

    @property
    def unready_names(self):
        return [ info[1]['name'] for info in self.unready_infos ]

    @property
    def names(self):
        return self.ready_names + self.unready_names

    def size(self):
        return len(self.ready_infos) + len(self.unready_infos)

    def __str__(self):
        return 'ready - [{}], unready - [{}]'.format(pprint.pformat([ info[1]['name'] for info in self.ready_infos]),
                                                     pprint.pformat([ info[1]['name'] for info in self.unready_infos]))



class CompsRestrictionTracker(RestrictionTracker):
    def __init__(self, comps_range):
        self.comps_range = comps_range
        self.ctx = None
        self.claimed = set()
        self.checkpointed = False
        self.params = Params.from_dict(self.comps_range.params_dict)

    def ensure_ctx(self):
        if self.ctx is None:
            self.ctx = Context(self.params)

    def check_done(self):
        self.ensure_ctx()

        all_comps = set(self.comps_range.names)
        all_downloaders = [ x for x in get_all_downloaders(self.ctx) if x in all_comps ]
        incomplete = [ x.name for x in all_downloaders if not x.is_done() ]
        if len(incomplete):
            raise ValueError(f'{incomplete} comps still not done')
        return True


    def current_restriction(self):
        return self.comps_range

    def current_progress(self):
        all_comps = set(self.comps_range.names)
        remaining = all_comps - self.claimed
        if len(all_comps):
            fraction_remaining = float(len(remaining)) / float(len(all_comps))
        else:
            fraction_remaining = 0.0

        return RestrictionProgress(fraction=(1.0 - fraction_remaining))


    def try_claim(self, comp):
        if comp in self.claimed:
            raise ValueError(f'{comp} already claimed')
        if comp in self.comps_range.names:
            self.claimed.add(comp)
            return True
        return False


    def try_split(self, fraction_of_remainder):
        logger.info(f'trying to split restriction with {fraction_of_remainder}')
        if self.checkpointed:
            return

        if fraction_of_remainder == 0:
            self.checkpointed = True

        self.ensure_ctx()
        ready_downloaders, unready_downloaders = redo_ready_unready_seperation(self.ctx,
                                                                               self.comps_range.ready_downloaders,
                                                                               self.comps_range.unready_downloaders)
        dmap_ready = {d.name:d for d in ready_downloaders}
        dmap_unready = {d.name:d for d in unready_downloaders}

        remainder_ready = set([ d.name for d in ready_downloaders ]) - self.claimed
        remainder_unready = set([ d.name for d in unready_downloaders ]) - self.claimed

        remainder = remainder_ready | remainder_unready
        num_to_pick = int(float(len(remainder)) * ( 1.0 - fraction_of_remainder ))
        if num_to_pick == 0:
            return 
        
        fragment_ready = []
        fragment_unready = []
        for i in range(num_to_pick):
            if len(remainder_ready):
                comp = remainder_ready.pop()
                fragment_ready.append(dmap_ready[comp])
                continue
            if len(remainder_unready):
                comp = remainder_unready.pop()
                fragment_unready.append(dmap_unready[comp])

        fragment_ready_infos = [ (x.__class__.__name__, x.get_kwargs()) for x in fragment_ready ]
        fragment_unready_infos = [ (x.__class__.__name__, x.get_kwargs()) for x in fragment_unready ]

        fragment_comps_range = CompsRange(ready_infos=fragment_ready_infos,
                                          unready_infos=fragment_unready_infos,
                                          params_dict=copy.copy(self.params.__dict__)) 

        base_ready = []
        base_unready = []
        while len(remainder_ready):
            comp = remainder_ready.pop()
            base_ready.append(dmap_ready[comp])
        while len(remainder_unready):
            comp = remainder_unready.pop()
            base_unready.append(dmap_unready[comp])

        base_ready_infos = [ (x.__class__.__name__, x.get_kwargs()) for x in base_unready ]
        base_unready_infos = [ (x.__class__.__name__, x.get_kwargs()) for x in base_ready ]

        base_comps_range = CompsRange(ready_infos=base_ready_infos,
                                      unready_infos=base_unready_infos,
                                      params_dict=copy.copy(self.params.__dict__)) 

        self.comps_range = base_comps_range
        return self.comps_range, fragment_comps_range


    def is_bounded(self):
        return True


def redo_ready_unready_seperation(ctx, ready_downloaders, unready_downloaders):
    ready_downloaders_expanded = expand_children(ready_downloaders)
    unready_downloaders_expanded = expand_children(unready_downloaders)
    downloaders = ready_downloaders_expanded + unready_downloaders_expanded
    comps = set([d.name for d in downloaders])

    all_downloaders_base = get_all_downloaders(ctx)

    all_downloaders_expanded = []
    all_dmap_expanded = {}
    for downloader in downloaders:
        all_downloaders_expanded.append(downloader)
        all_dmap_expanded[downloader.name] = downloader
    for downloader in all_downloaders_base:
        if downloader.name in all_dmap_expanded:
            continue
        all_downloaders_expanded.append(downloader)
        all_dmap_expanded[downloader.name] = downloader

    all_graph_expanded = {d.name:d.deps for d in all_downloaders_expanded}

    #logger.info('graph: {}'.format(pprint.pformat(all_graph_expanded)))

    #TODO: explain the need for all_*_expanded
    comps_expanded = expand_comps_to_run(comps, all_graph_expanded)
    graph_to_run = {d.name:d.deps for d in all_downloaders_expanded if d.name in comps_expanded}

    done = set()
    ready = set()

    ts = TopologicalSorter(graph_to_run)
    ts.prepare()
    while ts.is_active():
        new_ready = ts.get_ready()
        if len(new_ready) == 0:
            break
        for comp in new_ready:
            downloader = all_dmap_expanded[comp]
            #TODO: can be done using state in DoFn
            if downloader.is_done():
                ts.done(comp)
                done.add(comp)
            else:
                ready.add(comp)

    unready = set(comps_expanded) - (done | ready)

    return ([all_dmap_expanded[x] for x in ready],
            [all_dmap_expanded[x] for x in unready])


class DownloaderGenDoFn(DoFn, RestrictionProvider):

    def actual_processing(self, downloader):
        status = 'done'
        name = downloader.name
        logger.info(f'getting {downloader.desc} - {name}')
        try:
            downloader.download(self.ctx)
        except Exception:
            logger.exception(f'error with downloader: {name}')
            status = 'error'
        return (name, status)


    def process(self,
                element,
                tracker=DoFn.RestrictionParam()):

        logger.info('running process fn')
        self.ensure_ctx(Params.from_dict(element[1]))

        comps_range = tracker.current_restriction()
        logger.info('got restriction: {}'.format(comps_range))
        ready_downloaders = comps_range.ready_downloaders
        ready_downloaders.sort(key=lambda x:x.name)
        for downloader in ready_downloaders:
            comp_name = downloader.name
            if not tracker.try_claim(comp_name):
                return

            with MemoryTracker(downloader.name):
                res = self.actual_processing(downloader)
            yield res

        # trigger a checkpoint to let the split function redo the unready, ready assesment
        if len(comps_range.unready_infos):
            tracker.defer_remainder(Duration(10))

    def ensure_ctx(self, params):
        if getattr(self, 'ctx', None) is None:
            self.ctx = Context(params)

        # ensure downloader cache
        get_all_downloaders(self.ctx)

    def initial_restriction(self, element):
        comps_to_run = element[0]
        self.ensure_ctx(Params.from_dict(element[1]))

        downloaders = get_all_downloaders(self.ctx)
        downloaders = [ x for x in downloaders if x.name in comps_to_run ]
        ready_downloaders, unready_downloaders = redo_ready_unready_seperation(self.ctx, [], downloaders)

        ready_infos = [ (x.__class__.__name__, x.get_kwargs()) for x in ready_downloaders ]
        unready_infos = [ (x.__class__.__name__, x.get_kwargs()) for x in unready_downloaders ]

        comps_range = CompsRange(ready_infos, unready_infos, element[1])
        logger.info(f'creating initial restriction: {comps_range}')
        return comps_range

    # create tracker from restriction
    def create_tracker(self, comps_range):
        return CompsRestrictionTracker(comps_range)

    # estimate size of restriction
    def restriction_size(self, element, comps_range):
        return comps_range.size()

    # initial restriction split
    def split(self, element, comps_range):
        logger.info(f'manually splitting restriction: {comps_range}')
        self.ensure_ctx(Params.from_dict(element[1]))
        ready_downloaders, unready_downloaders = redo_ready_unready_seperation(self.ctx,
                                                                               comps_range.ready_downloaders,
                                                                               comps_range.unready_downloaders)

        ready_infos_map = { x.name:(x.__class__.__name__, x.get_kwargs()) for x in ready_downloaders }
        unready_infos_map = { x.name:(x.__class__.__name__, x.get_kwargs()) for x in unready_downloaders }

        unready = set([ d.name for d in unready_downloaders ])
        ready = set([ d.name for d in ready_downloaders ])

        for comp in ready:
            unready_to_add = [ unready.pop() ] if len(unready) else []
            yield CompsRange([ ready_infos_map[comp] ], [ unready_infos_map[x] for x in unready_to_add ], comps_range.params_dict)

        if len(unready):
            yield CompsRange([], [ unready_infos_map[x] for x in unready ], comps_range.params_dict)


def run_on_beam(comps_to_run, params, num_parallel):

    options = PipelineOptions()

    with Pipeline(options=options) as p:
        comps_status = ( p | Create([(comps_to_run, params.__dict__)])
                           | ParDo(DownloaderGenDoFn()) )

    return { 'done': [ x[0] for x in comps_status if x[1] == 'done' ],
             'error': [ x[0] for x in comps_status if x[1] == 'error' ] }
