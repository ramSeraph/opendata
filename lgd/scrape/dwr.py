import logging
import urllib.parse

from datetime import datetime
from pathlib import Path
from calmjs.parse import es5
from calmjs.parse.unparsers.extractor import ast_to_dict
from calmjs.parse.asttypes import FunctionCall

from .base import (DownloaderItem, BaseDownloader,
                   MultiDownloader)

logger = logging.getLogger(__name__)

def get_fn_call_args(name, ast_dict):
    fn_calls = ast_dict.get(FunctionCall, [])
    for fn_call in fn_calls:
        fn_name = fn_call[0]
        if fn_name == name:
            return fn_call[1]
    return None


class DwrCaller:
    def __init__(self,
                 ctx=None,
                 params=None,
                 base_url=None,
                 script_name='',
                 method_name='',
                 call_args={},
                 fields_to_keep=[],
                 fields_to_drop=[]):
        self.ctx=ctx
        self.params=params
        self.base_url=base_url
        self.script_name = script_name
        self.method_name = method_name
        self.call_args = call_args
        self.fields_to_keep = fields_to_keep
        self.fields_to_drop = fields_to_drop
        if len(fields_to_keep) and len(fields_to_drop):
            raise Exception('fields_to_drop and fields_to_keep both cant be non-empty together')


    def make_request(self, script_name, method_name, ref_url, extra_args={}):
        dwr_url = '{}/dwr/call/plaincall/{}.{}.dwr'.format(self.base_url, script_name, method_name)
        ref_url = urllib.parse.quote_plus(ref_url)
        post_data = {
            'callCount': '1',
            'windowName': '',
            'c0-scriptName': script_name,
            'c0-methodName': method_name,
            'c0-id': '0',
            'batchId': self.ctx.script_batch_id,
            'page': ref_url,
            'httpSessionId': '',
            'scriptSessionId': self.ctx.script_session_id
        }
        post_data.update(extra_args)

        post_data_strs = []
        for k,v in post_data.items():
            post_data_strs.append('{}={}'.format(k, v))

        post_data_full_str = '\n'.join(post_data_strs)


        logger.debug('making dwr call to url: {}, with data: {}'.format(dwr_url, post_data_full_str))
        web_data = self.ctx.session.post(dwr_url,
                                         data=post_data_full_str,
                                         headers={
                                             'Content-Type': 'text/plain'
                                         },
                                         **self.params.request_args())
        self.ctx.script_batch_id += 1
        if not web_data.ok:
            raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))

        content_type = web_data.headers['Content-Type']
        if content_type != 'text/javascript;charset=utf-8':
            raise Exception('Failed DWR request for {} expected javascript got {}'.format(self.name, content_type))

        try:
            js_resp = es5(web_data.text)
        except Exception:
            logger.error('unable to parse {} as js'.format(web_data.text))
            raise
        js_dict = ast_to_dict(js_resp)
        session_call_args = get_fn_call_args('dwr.engine.remote.handleNewScriptSession', js_dict)
        if session_call_args is not None:
            self.ctx.script_session_id = session_call_args[0]
            logger.info('got new script session id: {}'.format(self.ctx.script_session_id))
        return js_dict


    def ensure_session_id(self):
        if self.ctx.script_session_id != '':
            return

        self.make_request('__System', 'pageLoaded', '/downloadDirectory.do?OWASP_CSRFTOKEN={}'.format(self.ctx.csrf_token))
        if self.ctx.script_session_id == '':
            raise Exception('Unable to obtain new script session id')


    def marshal_dwr_data(self, data):
        fields_keep = set(self.fields_to_keep)
        fields_drop = set(self.fields_to_drop)
        all_fields_list = []
        if len(data) == 0:
            return []
        val = data[0]
        for key in val.keys():
            all_fields_list.append(key)

        all_fields = set(all_fields_list)

        use_fields = all_fields
        if len(fields_keep) > 0:
            unknown = fields_keep - all_fields
            logger.info('ignoring unknown fields {} while picking dwr return fields'.format(unknown))
            use_fields = fields_keep - unknown
        if len(fields_drop) > 0:
            use_fields = all_fields - fields_drop
        
        records = []
        for val in data:
            record = {}
            for k,v in val.items():
                if k not in use_fields:
                    continue
                if type(v) == list and len(v) == 2  and v[0] == 'Date' and len(v[1]) == 1:
                    v = datetime.fromtimestamp(v[1][0]/1000.0).strftime('%Y-%m-%d %H:%M:%S')
                record[k] = v
            records.append(record)
        return records


    def call(self):
        self.ensure_session_id()
        js_dict = self.make_request(self.script_name, self.method_name,
                                    '/downloadDirectory.do?OWASP_CSRFTOKEN={}'.format(self.ctx.csrf_token),
                                    extra_args=self.call_args)
        cb_args = get_fn_call_args('dwr.engine.remote.handleCallback', js_dict)
        if cb_args is None:
            raise Exception(f'unable to find callback function in dwr js: {js_dict}')
        data = cb_args[2]

        records = self.marshal_dwr_data(data)
        return records


class DwrDownloader(BaseDownloader):
    def __init__(self,
                 script_name='',
                 method_name='',
                 call_args={},
                 fields_to_keep=[],
                 fields_to_drop=[],
                 **kwargs):
        self.dwr_caller = None
        super().__init__(**kwargs)
        self.script_name = script_name
        self.method_name = method_name
        self.call_args = call_args
        self.fields_to_keep = fields_to_keep
        self.fields_to_drop = fields_to_drop
        self.dwr_caller = DwrCaller(params=self.params,
                                    ctx=self.ctx,
                                    base_url=self.base_url,
                                    script_name=script_name,
                                    method_name=method_name,
                                    call_args=call_args,
                                    fields_to_keep=fields_to_keep,
                                    fields_to_drop=fields_to_drop)


    def set_context(self, ctx):
        super().set_context(ctx)
        if self.dwr_caller is not None:
            self.dwr_caller.ctx = ctx


    def get_records(self):
        logger.info('making dwr call for {}'.format(self.name))
        return self.dwr_caller.call()
        

class StateWiseDwrDownloader(MultiDownloader, DwrDownloader):
    def __init__(self, **kwargs):
        if 'enrichers' not in kwargs:
            kwargs['enrichers'] = { 'State Code': 'State Code',
                                    'State Name': 'State Name(In English)' }
        if 'deps' not in kwargs:
            kwargs['deps'] = []
        if 'STATES' not in kwargs['deps']:
            kwargs['deps'].append('STATES')
        super().__init__(**kwargs)


    def populate_downloaders(self):
        if self.downloader_items is not None:
            return

        downloader_items = []
        for r in BaseDownloader.records_from_downloader('STATES'):
            state_code = r['State Code']
            state_name = r['State Name(In English)']

            csv_path = Path(self.csv_filename)
            csv_filename_s = str(csv_path.with_stem('{}_{}'.format(csv_path.stem, state_code)))
            downloader = DwrDownloader(name='{}_{}'.format(self.name, state_code),
                                       desc='{} for state {}({})'.format(self.desc, state_name, state_code),
                                       csv_filename=csv_filename_s,
                                       params=self.params,
                                       ctx=self.ctx,
                                       script_name=self.script_name,
                                       method_name=self.method_name,
                                       fields_to_drop=self.fields_to_drop,
                                       fields_to_keep=self.fields_to_keep,
                                       call_args={
                                           'c0-param0': f'number:{state_code}'
                                       })
            downloader_items.append(DownloaderItem(downloader=downloader, record=r))
        self.downloader_items = downloader_items


def get_all_dwr_downloaders(params, ctx):
    downloaders = []
    downloaders.append(DwrDownloader(name='CENTRAL_ADMIN_DEPTS',
                                     desc='list of all central administrative departments',
                                     section='Download Directory',
                                     dropdown='Department/Organization --> Administrative Unit Level Wise Administrative Unit Entity --> Central --> Internal Dwr Call',
                                     csv_filename='central_admin_depts.csv',
                                     script_name='lgdAdminDepatmentDwr',
                                     method_name='getAdministrationLevelList',
                                     fields_to_drop=[
                                         'buttonClicked',
                                         'operation_state',
                                         'sortOrder',
                                         'seqLevel',
                                         'slc'
                                     ],
                                     params=params,
                                     ctx=ctx,
                                     call_args={
                                         'c0-param0': 'number:0'
                                     }))

    downloaders.append(StateWiseDwrDownloader(name='STATE_ADMIN_DEPTS',
                                              desc='list of all state administrative departments',
                                              section='Download Directory',
                                              dropdown='Department/Organization --> Administrative Unit Level Wise Administrative Unit Entity --> State --> Internal Dwr Call',
                                              csv_filename='state_admin_depts.csv',
                                              script_name='lgdAdminDepatmentDwr',
                                              method_name='getAdministrationLevelList',
                                              fields_to_drop=[
                                                  'buttonClicked',
                                                  'operation_state',
                                                  'sortOrder',
                                                  'seqLevel',
                                                  'slc'
                                              ],
                                              params=params,
                                              ctx=ctx))

    return downloaders

