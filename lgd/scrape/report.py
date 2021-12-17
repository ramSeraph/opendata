import re
import io
import copy
import time
import logging

from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, parse_qs
from datetime import datetime, timedelta

from .base import (INCORRECT_CAPTCHA_MESSAGE,
                   BaseDownloader, MultiDownloader, 
                   DownloaderItem, get_date_str)
from .conversion_helper import records_from_excel

logger = logging.getLogger(__name__)


# from https://stackoverflow.com/a/52373377
def merge_url_query_params(url, additional_params):
    url_components = urlparse(url)
    original_params = parse_qs(url_components.query)
    # Before Python 3.5 you could update original_params with 
    # additional_params, but here all the variables are immutable.
    merged_params = {**original_params, **additional_params}
    updated_query = urlencode(merged_params, doseq=True)
    # _replace() is how you can create a new NamedTuple with a changed field
    return url_components._replace(query=updated_query).geturl()



class ReportDownloader(BaseDownloader):
    def __init__(self,
                 sub_url='',
                 post_data={},
                 query_data={},
                 oprand_data_extra={},
                 allow_empty=False,
                 **kwargs):
        kwargs['section'] = 'Reports'
        self.sub_url = sub_url
        self.post_data = post_data
        self.query_data = query_data
        self.allow_empty = allow_empty
        self.oprand_data_extra = oprand_data_extra
        super().__init__(**kwargs)

    def set_context(self, ctx):
        if ctx.csrf_token is not None:
            self.post_data['OWASP_CSRFTOKEN'] = ctx.csrf_token
            self.query_data['OWASP_CSRFTOKEN'] = ctx.csrf_token
        super().set_context(ctx)

    def get_records(self):
        report_base_url = '{}/{}'.format(self.base_url, self.sub_url)
        q_str = urlencode(self.query_data)
        referer_url = '{}?{}'.format(report_base_url, q_str)
        post_headers = {
            'referer': referer_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
        count = 0
        while True:
            captcha_code = self.captcha_helper.get_code(referer_url)
    
            post_form_data = copy.copy(self.post_data)
            post_form_data.update({
                'captchaAnswer': captcha_code
            })
            logger.debug('posting with captcha to {}'.format(report_base_url))
            web_data = self.ctx.session.post(report_base_url,
                                             data=post_form_data,
                                             headers=post_headers,
                                             **self.params.request_args())
            if not web_data.ok:
                raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))
    
            
            if INCORRECT_CAPTCHA_MESSAGE in web_data.text:
                self.captcha_helper.mark_failure()
                if count > 5:
                    raise Exception('failed after trying for 5 times')
                time.sleep(1)
                count += 1
                continue
    
            self.captcha_helper.mark_success()
            break
    
        birt_form_data = {}
        soup = BeautifulSoup(web_data.text, 'html.parser')
        birt_params_div = soup.find('div', { "id" : "params_birtViewer" })
        birt_inputs = birt_params_div.find_all('input')
        for birt_input in birt_inputs:
            birt_form_data[birt_input.attrs['name']] = birt_input.attrs['value']
    
        birt_seg_url_loc = web_data.text.find('/LIVE-BIRT/frameset')
        if birt_seg_url_loc == -1:
            raise Exception('unable to locate birt url segment')
        match = re.match(r'(/LIVE-BIRT/frameset.*)";', web_data.text[birt_seg_url_loc:])
        if match is None:
            raise Exception('unexpected format of birt url segment')
        birt_seg_url = match.group(1)
        logger.debug('got birt seg url: {}'.format(birt_seg_url))
        birt_url = '{}{}'.format(self.base_url, birt_seg_url)
    
        num_attempts = 0
        while True:
            session_id, oprand_data = self.get_birt_session_id(birt_url, birt_form_data, report_base_url)
            num_attempts += 1
            if session_id is not None:
                break
            if num_attempts < 5:
                time.sleep(5)
                continue
            break
    
        if session_id is None:
            raise Exception("Couldn't get birt session id")
    
    
        # wait till the soap call returns before exporting
        self.make_birt_soap_call(birt_url, session_id, oprand_data)
        xls_data = self.get_birt_export(birt_url, session_id)
    
        if xls_data is None:
            return []
    
        data_file = io.BytesIO(xls_data)
        return records_from_excel(data_file)


    def get_birt_session_id(self, birt_url, birt_form_data, report_base_url):
        birt_headers = {
            'referer': report_base_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        logger.debug('posting for session id to {}'.format(birt_url))
        web_data = self.ctx.session.post(birt_url,
                                         data=birt_form_data,
                                         headers=birt_headers,
                                         **self.params.request_args())
        if not web_data.ok:
            if web_data.status_code == 404:
                return None, None, None
            raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))
    
        session_id_snippet_loc = web_data.text.find('Constants.viewingSessionId')
        if session_id_snippet_loc == -1:
            raise Exception("couldn't find session id in birt page")
    
        match = re.match(r'Constants.viewingSessionId[ ]*=[ ]*"(.*)"[ ]*;', web_data.text[session_id_snippet_loc:])
        if match is None:
            raise Exception('unexpected format of session id string')
    
        session_id = match.group(1)
        logger.debug('got session id: {}'.format(session_id))
        #cookies = web_data.headers['Set-Cookie']
        #cookie = cookies.split(';')[0]
        #cookie = cookie.replace(',', ';')
    
        oprand_data = {}
        soup = BeautifulSoup(web_data.text, 'html.parser')
    
        param_div = soup.find('div', { "class" : "birtviewer_parameter_dialog" })
        inputs = param_div.find_all('input', attrs={ "class": "BirtViewer_parameter_dialog_Input" })
        for inp in inputs:
            oprand_data[inp.attrs['id']] = inp.attrs['value']

        oprand_data.update(self.oprand_data_extra)
    
        logger.debug(f'oprand_data: {oprand_data}')
        return session_id, oprand_data


    def make_birt_soap_call(self, birt_url, session_id, oprand_data):
        extra_oprand_txt = ""
        for k, v in oprand_data.items():
            extra_oprand_txt += "<Oprand><Name>{}</Name><Value>{}</Value></Oprand>\n".format(k,v)
            extra_oprand_txt += "<Oprand><Name>__isdisplay__{}</Name><Value>{}</Value></Oprand>\n".format(k,v)
    
        soap_body = """
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <GetUpdatedObjects xmlns="http://schemas.eclipse.org/birt">
                    <Operation>
                        <Target>
                            <Id>Document</Id>
                            <Type>Document</Type>
                        </Target>
                        <Operator>GetPage</Operator>
        """ +\
                extra_oprand_txt +\
        """
                        <Oprand>
                            <Name>__page</Name>
                            <Value>1</Value>
                        </Oprand>
                        <Oprand>
                            <Name>__svg</Name>
                            <Value>true</Value>
                        </Oprand>
                        <Oprand>
                            <Name>__page</Name>
                            <Value>1</Value>
                        </Oprand>
                        <Oprand>
                            <Name>__taskid</Name>
                            <Value>{}</Value>
                        </Oprand>
                    </Operation>
                </GetUpdatedObjects>
            </soap:Body>
        </soap:Envelope>
        """.format(session_id)
    
        #headers['Cookie'] = '{}; {}'.format(cookie, headers['Cookie'])
        headers = {
            'referer': birt_url,
            'Content-Type': 'text/xml; charset=UTF-8; charset=UTF-8',
            'request-type': 'SOAP',
            'SOAPAction': ''
        }
    
        soap_url_full = merge_url_query_params(birt_url, {
                '__sessionId': session_id,
                '__dpi': '96',
        })
        logger.debug('sending soap request to {}.. to initiate processing'.format(soap_url_full))
        web_data = self.ctx.session.post(soap_url_full,
                                         data=soap_body,
                                         headers=headers,
                                         **self.params.request_args())
        if not web_data.ok:
            raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))


    def get_birt_export(self, birt_url, session_id):
        #headers['Cookie'] = '{}; {}'.format(cookie, headers['Cookie'])
        headers = {
            'referer': birt_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
        export_url_full = merge_url_query_params(birt_url, {
                '__sessionId': session_id,
                '__dpi': '96',
                '__format': 'xls',
                '__asattachment': 'true',
                '__overwrite': 'false'
        })
        logger.debug('posting to {} for exporting data as xls'.format(export_url_full))
        web_data = self.post_with_progress(export_url_full, data={}, headers=headers)
        if not web_data.ok:
            raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))
    
        if web_data.headers['Content-Type'] != 'application/vnd.ms-excel':
            return None
        return web_data.content


class StateWiseReportDownloader(MultiDownloader, ReportDownloader):
    def __init__(self, **kwargs):
        if 'enrichers' not in kwargs:
            kwargs['enrichers'] = { 'State Code': 'State Code',
                                    'State Name': 'State Name(In English)' }

        if 'deps' not in kwargs:
            kwargs['deps'] = []

        if 'STATES' not in kwargs:
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
            downloader = ReportDownloader(name='{}_{}'.format(self.name, state_code),
                                          desc='{} for state {}({})'.format(self.desc, state_name, state_code),
                                          csv_filename=csv_filename_s,
                                          sub_url=self.sub_url,
                                          allow_empty=self.allow_empty,
                                          params=self.params,
                                          ctx=self.ctx,
                                          post_data={
                                              'entityname': state_code,
                                              'code': state_code
                                          },
                                          oprand_data_extra={
                                              'stateName': state_name
                                          })
            downloader_items.append(DownloaderItem(downloader=downloader, record=r))
        self.downloader_items = downloader_items


class DateWiseReportDownloader(MultiDownloader, ReportDownloader):
    def __init__(self,
                 num_dates=0,
                 **kwargs):
        if 'enrichers' not in kwargs:
            kwargs['enrichers'] = { 'date': 'date' }
        if 'delete_intermediates' not in kwargs:
            kwargs['delete_intermediates'] = False
        super().__init__(**kwargs)
        self.max_delta = num_dates

    def populate_downloaders(self):
        if self.downloader_items is not None:
            return
        today = datetime.today()
        delta = 0

        downloader_items = []
        while delta < self.max_delta:
            old_date = today - timedelta(days=delta)
            old_date_str = old_date.strftime("%d-%m-%Y")
            prev_date = old_date - timedelta(days=1)
            prev_date_str = prev_date.strftime("%d-%m-%Y")

            csv_path = Path(self.csv_filename)
            csv_filename_s = str(csv_path.with_stem('{}'.format(old_date_str)))
            #TODO: too specific to changes and convoluted
            full_path = Path('changes').joinpath(f'{old_date_str}.csv')
            downloader = ReportDownloader(name='{}_{}'.format(self.name, old_date_str),
                                          desc='{} for date {}'.format(self.desc, old_date_str),
                                          sub_url=self.sub_url,
                                          csv_filename=csv_filename_s,
                                          full_filename=str(full_path),
                                          params=self.params,
                                          ctx=self.ctx,
                                          post_data={
                                              'fromDate': prev_date_str,
                                              'toDate': old_date_str,
                                              'fromDates': prev_date_str,
                                              'toDates': old_date_str
                                          },
                                          enrichers={
                                              'date': get_date_str(prev_date)
                                          })
            downloader_items.append(DownloaderItem(downloader=downloader, record={'date': old_date_str}))
            delta += 1
        self.downloader_items = downloader_items


def get_all_report_downloaders(params, ctx):
    downloaders = []
    downloaders.append(ReportDownloader(name='INVALIDATED_VILLAGES',
                                        desc='list of all invalidated census villages',
                                        dropdown='Exceptional Reports --> Invalidated Census villages',
                                        csv_filename='invalidated_census_villages.csv',
                                        sub_url='exceptionalReports.do',
                                        params=params,
                                        ctx=ctx,
                                        post_data={
                                            'reportName': 'Invalidated Census villages',
                                            'fileName': 'ER_InvalidateCensusVillage',
                                        },
                                        query_data={
                                            'reportName': 'Invalidated Census villages',
                                            'fileName': 'ER_InvalidateCensusVillage',
                                        }))

    downloaders.append(StateWiseReportDownloader(name='NOFN_PANCHAYATS',
                                                 desc='list of all panchayats with NOFN',
                                                 dropdown='NOFN Panchayat List',
                                                 csv_filename='nofn_panchayats.csv',
                                                 sub_url='nofnStates.do',
                                                 params=params,
                                                 ctx=ctx))
    downloaders.append(DateWiseReportDownloader(name='CHANGES',
                                                desc='all changes to entities in LGD',
                                                dropdown='List of Modification done in LGD',
                                                csv_filename='changes.csv',
                                                sub_url='changedEntity.do',
                                                params=params,
                                                ctx=ctx,
                                                num_dates=4000))

    return downloaders
