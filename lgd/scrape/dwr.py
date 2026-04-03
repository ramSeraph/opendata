import logging
import random
import time
import urllib.parse

from datetime import datetime
from pathlib import Path

from calmjs.parse import es5
from calmjs.parse.unparsers.extractor import ast_to_dict
from calmjs.parse.asttypes import FunctionCall

from .base import (DownloaderItem, BaseDownloader,
                   MultiDownloader, add_defaults_to_args)

logger = logging.getLogger(__name__)

DWR_TOKEN_CHARMAP = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ*$'

def get_fn_call_args(name, ast_dict):
    if isinstance(ast_dict, dict):
        fn_calls = ast_dict.get(FunctionCall, [])
        for fn_call in fn_calls:
            if not isinstance(fn_call, list) or len(fn_call) < 2:
                continue
            fn_name = fn_call[0]
            if fn_name == name:
                return fn_call[1]
        for value in ast_dict.values():
            call_args = get_fn_call_args(name, value)
            if call_args is not None:
                return call_args
    elif isinstance(ast_dict, list):
        for value in ast_dict:
            call_args = get_fn_call_args(name, value)
            if call_args is not None:
                return call_args
    return None


def tokenify(number):
    tokenbuf = []
    remainder = int(number)
    while remainder > 0:
        tokenbuf.append(DWR_TOKEN_CHARMAP[remainder & 0x3F])
        remainder = remainder // 64
    if len(tokenbuf) == 0:
        return DWR_TOKEN_CHARMAP[0]
    return ''.join(tokenbuf)


class DwrCaller:
    def __init__(self,
                 ctx=None,
                 base_url=None,
                 script_name='',
                 method_name='',
                 call_args=None,
                 fields_to_keep=None,
                 fields_to_drop=None):
        self.ctx=ctx
        self.base_url=base_url
        self.script_name = script_name
        self.method_name = method_name
        self.call_args = call_args or {}
        self.fields_to_keep = fields_to_keep or []
        self.fields_to_drop = fields_to_drop or []
        if len(self.fields_to_keep) and len(self.fields_to_drop):
            raise Exception('fields_to_drop and fields_to_keep both cant be non-empty together')


    def get_request_name(self, script_name, method_name):
        return '{}.{}'.format(script_name, method_name)


    def get_ref_url(self):
        return '/downloadDirectory.do?OWASP_CSRFTOKEN={}'.format(self.ctx.csrf_token)


    def get_instance_id(self):
        instance_id = getattr(self.ctx, 'dwr_instance_id', None)
        if instance_id is None:
            instance_id = 0
            self.ctx.dwr_instance_id = instance_id
        return instance_id


    def get_page_id(self):
        page_id = getattr(self.ctx, 'dwr_page_id', None)
        if page_id is not None:
            return page_id

        page_id = '{}-{}'.format(
            tokenify(round(time.time() * 1000)),
            tokenify(random.getrandbits(53))
        )
        self.ctx.dwr_page_id = page_id
        return page_id


    def get_dwr_session_id(self):
        dwr_session_id = getattr(self.ctx, 'dwr_session_id', None)
        if dwr_session_id is not None:
            return dwr_session_id

        dwr_session_id = self.ctx.session.cookies.get('DWRSESSIONID')
        if dwr_session_id is not None:
            self.ctx.dwr_session_id = dwr_session_id
        return dwr_session_id


    def raise_on_batch_error(self, script_name, method_name, js_dict):
        batch_exception = get_fn_call_args('dwr.engine.remote.handleBatchException', js_dict)
        if batch_exception is None:
            return

        if len(batch_exception) == 0 or not isinstance(batch_exception[0], dict):
            raise Exception('Failed DWR request for {} with malformed batch exception: {}'.format(
                self.get_request_name(script_name, method_name), batch_exception))

        error = batch_exception[0]
        error_name = error.get('name', 'unknown')
        error_message = error.get('message', '')
        raise Exception('Failed DWR request for {}: {}: {}'.format(
            self.get_request_name(script_name, method_name), error_name, error_message))


    def make_request(self, script_name, method_name, ref_url, extra_args=None, script_session_id=None):
        dwr_url = '{}/dwr/call/plaincall/{}.{}.dwr'.format(self.base_url, script_name, method_name)
        ref_url = urllib.parse.quote(ref_url, safe='')
        post_data = {
            'callCount': '1',
            'windowName': '',
            'c0-scriptName': script_name,
            'c0-methodName': method_name,
            'c0-id': '0',
            'batchId': self.ctx.script_batch_id,
            'instanceId': self.get_instance_id(),
            'page': ref_url,
            'scriptSessionId': self.ctx.script_session_id if script_session_id is None else script_session_id
        }
        if extra_args is not None:
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
                                         **self.ctx.params.request_args())
        self.ctx.script_batch_id += 1
        if not web_data.ok:
            raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))

        content_type = web_data.headers.get('Content-Type', '')
        content_type_main = content_type.split(';')[0].strip().lower()
        if content_type_main != 'text/javascript':
            raise Exception('Failed DWR request for {} expected javascript got {}'.format(
                self.get_request_name(script_name, method_name), content_type))

        try:
            js_resp = es5(web_data.text)
        except Exception:
            logger.error('unable to parse {} as js'.format(web_data.text))
            raise
        js_dict = ast_to_dict(js_resp)
        self.raise_on_batch_error(script_name, method_name, js_dict)
        return js_dict


    def ensure_session_id(self):
        if self.ctx.script_session_id != '':
            return

        dwr_session_id = self.get_dwr_session_id()
        if dwr_session_id is None:
            js_dict = self.make_request('__System', 'generateId', self.get_ref_url(), script_session_id='')
            cb_args = get_fn_call_args('dwr.engine.remote.handleCallback', js_dict)
            if cb_args is None or len(cb_args) < 3 or not isinstance(cb_args[2], str):
                raise Exception('Unable to obtain DWR session id from response: {}'.format(js_dict))
            dwr_session_id = cb_args[2]
            self.ctx.dwr_session_id = dwr_session_id
            self.ctx.session.cookies.set('DWRSESSIONID', dwr_session_id, path='/')

        self.ctx.script_session_id = '{}/{}'.format(dwr_session_id, self.get_page_id())


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
                                    self.get_ref_url(),
                                    extra_args=self.call_args)
        cb_args = get_fn_call_args('dwr.engine.remote.handleCallback', js_dict)
        if cb_args is None:
            raise Exception('unable to find callback function in dwr js for {}: {}'.format(
                self.get_request_name(self.script_name, self.method_name), js_dict))
        data = cb_args[2]

        records = self.marshal_dwr_data(data)
        return records


class DwrDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        kwargs = add_defaults_to_args({ 'script_name': '',
                                        'method_name':'',
                                        'call_args': {},
                                        'fields_to_keep': [],
                                        'fields_to_drop': []}, kwargs)
        self.dwr_caller = None
        super().__init__(**kwargs)
        self.script_name = kwargs['script_name']
        self.method_name = kwargs['method_name']
        self.call_args = kwargs['call_args']
        self.fields_to_keep = kwargs['fields_to_keep']
        self.fields_to_drop = kwargs['fields_to_drop']
        self.dwr_caller = DwrCaller(ctx=self.ctx,
                                    base_url=self.base_url,
                                    script_name=self.script_name,
                                    method_name=self.method_name,
                                    call_args=self.call_args,
                                    fields_to_keep=self.fields_to_keep,
                                    fields_to_drop=self.fields_to_drop)


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
                                    'State Name': 'State Name (In English)' }
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
            state_name = r['State Name (In English)']

            csv_path = Path(self.csv_filename)
            csv_filename_s = '{}_{}{}'.format(csv_path.stem, state_code, csv_path.suffix)
            downloader = DwrDownloader(name='{}_{}'.format(self.name, state_code),
                                       base_name=self.name,
                                       desc='{} for state {}({})'.format(self.desc, state_name, state_code),
                                       csv_filename=csv_filename_s,
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


def get_all_dwr_downloaders(ctx):
    downloaders = []
    downloaders.append(DwrDownloader(name='CENTRAL_ADMIN_DEPTS',
                                     script_name='lgdAdminDepatmentDwr',
                                     method_name='getAdministrationLevelList',
                                     fields_to_drop=[
                                         'buttonClicked',
                                         'operation_state',
                                         'sortOrder',
                                         'seqLevel',
                                         'slc'
                                     ],
                                     ctx=ctx,
                                     call_args={
                                         'c0-param0': 'number:0'
                                     }))

    downloaders.append(StateWiseDwrDownloader(name='STATE_ADMIN_DEPTS',
                                              script_name='lgdAdminDepatmentDwr',
                                              method_name='getAdministrationLevelList',
                                              fields_to_drop=[
                                                  'buttonClicked',
                                                  'operation_state',
                                                  'sortOrder',
                                                  'seqLevel',
                                                  'slc'
                                              ],
                                              ctx=ctx))

    return downloaders
