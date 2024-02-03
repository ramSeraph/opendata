import os
import os.path
import time
import copy
import logging

from datetime import datetime, timedelta
from pathlib import Path
from .base import (INCORRECT_CAPTCHA_MESSAGE,
                   DownloaderItem, BaseDownloader,
                   MultiDownloader, add_defaults_to_args)
from .conversion_helper import (records_from_excel, records_from_xslx,
                                unzip_single, records_from_odt,
                                records_from_htm)

logger = logging.getLogger(__name__)


class CaptchaFailureException(Exception):
    pass

def merge_file(old_file, mod_file, tgt_file):
    #TODO: write this
    pass



class DirectoryDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        kwargs = add_defaults_to_args({'post_data_extra':{},
                                       'odt_conv_args':{},
                                       'excel_conv_args':{},
                                       'download_types': ['xls']}, kwargs)
        self.post_data = {
            "DDOption": "UNSELECT",
            "downloadOption": "DFD",
            "entityCode": "-1",
            "_multiRptFileNames": ["on"] * 12,
            "fromDate": None,
            "toDate": None,
            "fromDate2": None,
            "toDate2": None,
            "rptFileNameMod": "0",
            "entityCodes": [ '35', None ],
            "stateName": [ 'ANDAMAN AND NICOBAR ISLANDS', None, None ],
            "districtName": [ None ] * 3,
            "blockName": [ None ] * 3,
            "lbl": None,
        }
        self.post_data.update(kwargs['post_data_extra'])
        self.odt_conv_args = kwargs['odt_conv_args']
        self.excel_conv_args = kwargs['excel_conv_args']
        self.download_types = kwargs['download_types']
        super().__init__(**kwargs)


    def make_request(self, download_type):
        download_dir_url = '{}/downloadDirectory.do?OWASP_CSRFTOKEN={}'.format(self.base_url, self.ctx.csrf_token)
        post_data = copy.copy(self.post_data)
        captcha_code = self.captcha_helper.get_code(download_dir_url)
        post_data['captchaAnswer'] = captcha_code
        post_data['OWASP_CSRFTOKEN'] = self.ctx.csrf_token
        post_data['downloadType'] = download_type
        post_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'referer': download_dir_url
        }
        web_data = self.post_with_progress(download_dir_url,
                                           data=post_data,
                                           headers=post_headers)
        if not web_data.ok:
            raise Exception('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))

        if 'Content-Disposition' not in web_data.headers or 'attachment;' not in web_data.headers['Content-Disposition']:
            if INCORRECT_CAPTCHA_MESSAGE  not in web_data.text:
                if self.ctx.params.save_failed_html:
                    with open('failed.html', 'w') as f:
                        f.write(web_data.text)
                raise Exception('Non-captcha failure in request')
    
            self.captcha_helper.mark_failure()
            raise CaptchaFailureException()
   
        self.captcha_helper.mark_success()
        suffix = None
        content_type = web_data.headers['Content-Type']
        content = web_data.content
        if content_type == 'application/zip;charset=UTF-8':
            logger.debug('unzipping data')
            filename, content = unzip_single(content)
            logger.debug(f'unzipped filename: {filename}')
            suffix = Path(filename).suffix
    
        if content_type == 'odt;charset=UTF-8':
            suffix ='.odt'

        if content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=UTF-8':
            suffix = '.xlsx'

        if content_type == 'text/html;charset=UTF-8':
            suffix = '.htm'

        if content_type == 'xls;charset=UTF-8':
            suffix = '.xls'
    
        
    
        if suffix is None:
            raise Exception(f"unrecongonized content type: {content_type}")
    
        try:
            data_file_name = self.get_temp_file(content, suffix)
            del content
            del web_data
            with open(data_file_name, 'rb') as data_file:
                records = []
                if suffix == '.xlsx':
                    records = records_from_xslx(data_file)
                elif suffix == '.odt':
                    records = records_from_odt(data_file, **self.odt_conv_args)
                elif suffix == '.htm':
                    records = records_from_htm(data_file)
                elif suffix == '.xls':
                    records = records_from_excel(data_file, **self.excel_conv_args)
                else:
                    raise Exception(f"unsupprted suffix: {suffix}")
        finally:
            if not self.ctx.params.save_intermediates:
                Path(data_file_name).unlink(missing_ok=True)
            else:
                logger.info(f'intermediate {data_file_name=}')

        #logger.debug('got {} records'.format(len(records)))
        #logger.debug('{}'.format(records[0]))
        return records


    def get_records(self):
        download_types = copy.copy(self.download_types)
        while True:
            download_type = download_types.pop(0)
            try:
                count = 0
                while True:
                    count += 1
                    try:
                        return self.make_request(download_type)
                    except CaptchaFailureException:
                        if count > 5:
                            raise Exception('captcha failed for 5 tries')
                        time.sleep(1)
            except Exception as ex:
                if len(download_types) == 0:
                    raise ex
                else:
                    logger.warning(f'Caught exception while running with download_type: {download_type}.. checking with other downloadtypes', exc_info=True)


    #TODO: this is incomplete
    def get_file_mod(self):
    
        if not self.ctx.params.using_mods:
            self.get_file()
            return
    
        csv_filename = self.get_filename()
        dir_name = os.path.dirname(csv_filename)
        file_name = os.path.basename(csv_filename)
        old_csv_filename = csv_filename
        csv_filename = f'{dir_name}/mods/{file_name}'
        self.post_data['downloadOption'] = 'DMO'
        self.post_data['rptFileNameMod'] = self.post_data['rptFileName'] + 'byDate' 
        self.post_data['rptFileName'] = '-1'
        self.post_data['fromDate'] = MOD_FROM_DATE
        self.post_data['toDate'] = MOD_TO_DATE
        dir_dir_name = os.path.dirname(dir_name)
        old_file = f'{dir_dir_name}/{MOD_FROM_DATE}/{file_name}'
    
        if os.path.exists(csv_filename):
            merge_file(old_file, csv_filename, old_csv_filename) 
            os.remove(csv_filename)
            return
    
        # TODO: use changed filename
        self.get_file()
        merge_file(old_file, csv_filename, old_csv_filename) 
        os.remove(csv_filename)





class StateWiseDirectoryDownloader(MultiDownloader, DirectoryDownloader):
    def __init__(self, **kwargs):
        if 'enrichers' not in kwargs:
            kwargs['enrichers'] = { 'State Code': 'State Code',
                                    'State Name': 'State Name(In English)' }
        if 'deps' not in kwargs:
            kwargs['deps'] = []
        if 'STATES' not in kwargs['deps']:
            kwargs['deps'].append('STATES')
        super().__init__(**kwargs)
        self.post_data_extra = kwargs.get('post_data_extra', {})

    def populate_downloaders(self):
        if self.downloader_items is not None:
            return
        downloader_items = []
        for r in BaseDownloader.records_from_downloader('STATES'):
            state_code = r['State Code']
            state_name = r['State Name(In English)']

            csv_path = Path(self.csv_filename)
            csv_filename_s = '{}_{}{}'.format(csv_path.stem, state_code, csv_path.suffix)
            post_data_extra = copy.copy(self.post_data_extra)
            post_data_extra.update({ 'stateName': state_name,
                                     'entityCodes': state_code })
            downloader = DirectoryDownloader(name='{}_{}'.format(self.name, state_code),
                                             desc='{} for state {}({})'.format(self.desc, state_name, state_code),
                                             csv_filename=csv_filename_s,
                                             ctx=self.ctx,
                                             transform=self.transform,
                                             download_types=self.download_types,
                                             odt_conv_args=self.odt_conv_args,
                                             excel_conv_args=self.excel_conv_args,
                                             post_data_extra=post_data_extra)
            downloader_items.append(DownloaderItem(downloader=downloader, record=r))
        self.downloader_items = downloader_items


class OrgWiseDirectoryDownloader(MultiDownloader, DirectoryDownloader):
    def __init__(self, **kwargs):
        kwargs = add_defaults_to_args({'depends_on': ''}, kwargs)
        if 'deps' not in kwargs:
            kwargs['deps'] = []

        depends_on = kwargs['depends_on']
        if depends_on != '' and depends_on not in kwargs['deps']:
            kwargs['deps'].append(depends_on)
        super().__init__(**kwargs)
        self.depends_on = depends_on
        self.post_data_extra = kwargs.get('post_data_extra', {})

    def populate_downloaders(self):
        if self.downloader_items is not None:
            return

        downloader_items = []
        for r in BaseDownloader.records_from_downloader(self.depends_on):
            org_code = r['Organization Code']
            org_name = r['Organization Name']
            state_code = r.get('State Code', '0')
            state_name = r.get('State Name', 'India')

            csv_path = Path(self.csv_filename)
            csv_filename_s = '{}_{}{}'.format(csv_path.stem, org_code, csv_path.suffix)
            post_data_extra = copy.copy(self.post_data_extra)
            post_data_extra.update({ 'entityCodes': ['35', state_code, org_code] })
            downloader = DirectoryDownloader(name='{}_{}'.format(self.name, org_code),
                                             desc='{} for organization {}({}) of {}({})'\
                                                  .format(self.desc, org_name, org_code, state_name, state_code),
                                             csv_filename=csv_filename_s,
                                             ctx=self.ctx,
                                             excel_conv_args=self.excel_conv_args,
                                             post_data_extra=post_data_extra)
            downloader_items.append(DownloaderItem(downloader=downloader, record=r))
        self.downloader_items = downloader_items


class AdminDeptWiseDirectoryDownloader(MultiDownloader, DirectoryDownloader):
    def __init__(self, **kwargs):
        kwargs = add_defaults_to_args({'depends_on': ''}, kwargs)
        if 'deps' not in kwargs:
            kwargs['deps'] = []

        depends_on = kwargs['depends_on']
        if depends_on != '' and depends_on not in kwargs['deps']:
            kwargs['deps'].append(depends_on)
        super().__init__(**kwargs)
        self.depends_on = depends_on
        self.post_data_extra = kwargs.get('post_data_extra', {})

    def populate_downloaders(self):
        if self.downloader_items is not None:
            return
        downloader_items = []
        for r in BaseDownloader.records_from_downloader(self.depends_on):
            admin_dept_code = r['adminUnitCode']
            admin_dept_name = r['adminLevelNameEng']
            state_code = r.get('State Code', '0')
            state_name = r.get('State Name', 'India')

            to_date = datetime.today() - timedelta(1)
            #created_on = datetime.strptime(r['createdon'], '%Y-%m-%d %H:%M:%S') 
            #from_date = created_on - timedelta(1)
            from_date = to_date - timedelta(10000)

            from_str = from_date.strftime('%d-%m-%Y')
            to_str = to_date.strftime('%d-%m-%Y')

            csv_path = Path(self.csv_filename)
            csv_filename_s = '{}_{}{}'.format(csv_path.stem, admin_dept_code, csv_path.suffix)
            post_data_extra = copy.copy(self.post_data_extra)
            post_data_extra.update({'entityCodes': ['35', state_code, '', admin_dept_code],
                                    'lbl': 'FOOBAR',
                                    'fromDate2': from_str,
                                    'toDate2': to_str})
            downloader = DirectoryDownloader(name='{}_{}'.format(self.name, admin_dept_code),
                                             desc='{} for admin dept {}({}) of {}({})'\
                                                  .format(self.desc, admin_dept_name, admin_dept_code,
                                                          state_name, state_code),
                                             csv_filename=csv_filename_s,
                                             ctx=self.ctx,
                                             transform=self.transform,
                                             post_data_extra=post_data_extra)
            downloader_items.append(DownloaderItem(downloader=downloader, record=r))
        self.downloader_items = downloader_items


class ConstituencyWiseDirectoryDownloader(MultiDownloader, DirectoryDownloader):
    def __init__(self, **kwargs):
        if 'enrichers' not in kwargs:
            kwargs['enrichers'] = { 'State Code': 'State Code',
                                    'Parliament Constituency Code': 'Parliament Constituency Code' }
        if 'deps' not in kwargs:
            kwargs['deps'] = []
        if 'CONSTITUENCIES_PARLIAMENT' not in kwargs['deps']:
            kwargs['deps'].append('CONSTITUENCIES_PARLIAMENT')
        super().__init__(**kwargs)
        self.post_data_extra = kwargs.get('post_data_extra', {})


    def populate_downloaders(self):
        if self.downloader_items is not None:
            return
        downloader_items = []
        for r in BaseDownloader.records_from_downloader('CONSTITUENCIES_PARLIAMENT'):
            state_code = r['State Code']
            state_name = r['State Name']
            const_name = r['Parliament Constituency Name']
            const_code = r['Parliament Constituency Code']


            csv_path = Path(self.csv_filename)
            csv_filename_s = '{}_{}{}'.format(csv_path.stem, const_code, csv_path.suffix)
            post_data_extra = copy.copy(self.post_data_extra)
            post_data_extra.update({'stateName': state_name,
                                    'entityCodes': [state_code, const_code]})
            downloader = DirectoryDownloader(name='{}_{}_{}'.format(self.name, state_code, const_code),
                                             desc='{} for constituency {}({}) of state {}({})'.format(self.desc, const_name, const_code, state_name, state_code),
                                             csv_filename=csv_filename_s,
                                             ctx=self.ctx,
                                             post_data_extra=post_data_extra)
            downloader_items.append(DownloaderItem(downloader=downloader, record=r))
        self.downloader_items = downloader_items
 

def get_all_directory_downloaders(ctx):
    downloaders = []
    downloaders.append(DirectoryDownloader(name='STATES',
                                           desc='list of all states',
                                           csv_filename='states.csv',
                                           ctx=ctx,
                                           excel_conv_args={
                                               'header_row_span': 1,
                                           },
                                           post_data_extra={
                                               'rptFileName': 'allStateofIndia',
                                           }))
    downloaders.append(DirectoryDownloader(name='DISTRICTS',
                                           desc='list of all districts',
                                           csv_filename='districts.csv',
                                           ctx=ctx,
                                           excel_conv_args={
                                               'header_row_span': 2,
                                           },
                                           post_data_extra={
                                               'rptFileName': 'allDistrictofIndia',
                                           }))
    downloaders.append(DirectoryDownloader(name='SUB_DISTRICTS', 
                                           desc='list of all subdistricts',
                                           csv_filename='subdistricts.csv',
                                           ctx=ctx,
                                           post_data_extra={
                                               'rptFileName': 'allSubDistrictofIndia',
                                           }))
    downloaders.append(DirectoryDownloader(name='BLOCKS',
                                           desc='list of all blocks',
                                           csv_filename='blocks.csv',
                                           ctx=ctx,
                                           excel_conv_args={
                                               'header_row_span': 2,
                                           },
                                           post_data_extra={
                                               'rptFileName': 'allBlockofIndia',
                                           }))
    # Too big.. had to break to statewise downloads
    #downloaders.append(DirectoryDownloader(name='VILLAGES',
    #                                       desc='list of all villages',
    #                                       csv_filename='villages.csv',
    #                                       ctx=ctx,
    #                                       post_data_extra={
    #                                           'rptFileName': 'allVillagesofIndia',
    #                                       }))
    #downloaders.append(DirectoryDownloader(name='BLOCK_VILLAGES',
    #                                       desc='list of all village to block mappings',
    #                                       csv_filename='villages_by_blocks.csv',
    #                                       ctx=ctx,
    #                                       post_data_extra={
    #                                           'rptFileName': 'subdistrictVillageBlockGpsMapping',
    #                                       }))
    #downloaders.append(DirectoryDownloader(name='PRI_LOCAL_BODIES',
    #                                       desc='list of all PRI(Panchayati Raj India) local bodies',
    #                                       csv_filename='pri_local_bodies.csv',
    #                                       ctx=ctx,
    #                                       post_data_extra={
    #                                           'rptFileName': 'priLocalBodyIndia',
    #                                           'downloadType': 'odt' # because the header came out unbroken in odt as opposed xls
    #                                       }))
    downloaders.append(DirectoryDownloader(name='TRADITIONAL_LOCAL_BODIES',
                                           desc='list of all Traditional local bodies',
                                           csv_filename='traditional_local_bodies.csv',
                                           ctx=ctx,
                                           excel_conv_args={
                                               'header_row_span': 2,
                                           },
                                           post_data_extra={
                                               'rptFileName': 'allTraditionalLBofInida',
                                           }))
    downloaders.append(DirectoryDownloader(name='URBAN_LOCAL_BODIES',
                                           desc='list of all urban local bodies',
                                           csv_filename='urban_local_bodies.csv',
                                           ctx=ctx,
                                           excel_conv_args={
                                               'header_row_span': 2,
                                           },
                                           post_data_extra={
                                               'rptFileName': 'urbanLocalBodyIndia',
                                           }))
    downloaders.append(DirectoryDownloader(name='URBAN_LOCAL_BODIES_COVERAGE',
                                           desc='list of all urban local bodies with coverage',
                                           csv_filename='statewise_ulbs_coverage.csv',
                                           ctx=ctx,
                                           excel_conv_args={
                                               'header_row_span': 2,
                                           },
                                           post_data_extra={
                                               'rptFileName': 'statewise_ulbs_coverage',
                                           }))
    #downloaders.append(DirectoryDownloader(name='CONSTITUENCIES_PARLIAMENT',
    #                                       desc='list of all parliament constituencies',
    #                                       csv_filename='parliament_constituencies.csv',
    #                                       ctx=ctx,
    #                                       transform=['ignore_if_empty_field', 'Parliament Constituency Code'],
    #                                       post_data_extra={
    #                                           'rptFileName': 'assembly_parliament_constituency',
    #                                           'stateName': 'India',
    #                                           'entityCodes': ['35', '0'],
    #                                           'assemblyParliamentConstituency': '#PC'
    #                                       }))
    #downloaders.append(DirectoryDownloader(name='CONSTITUENCIES_ASSEMBLY',
    #                                       desc='list of all assembly constituencies',
    #                                       csv_filename='assembly_constituencies.csv',
    #                                       ctx=ctx,
    #                                       post_data_extra={
    #                                           'rptFileName': 'assembly_parliament_constituency',
    #                                           'stateName': 'India',
    #                                           'entityCodes': ['35', '0'],
    #                                           'assemblyParliamentConstituency': '#AC'
    #                                       }))
    downloaders.append(DirectoryDownloader(name='PINCODE_VILLAGES',
                                           desc='Pincode to Village Mapping',
                                           csv_filename='pincode_villages.csv',
                                           ctx=ctx,
                                           post_data_extra={
                                               'rptFileName': 'pincodetoVillageMapping',
                                           }))
    downloaders.append(DirectoryDownloader(name='PINCODE_URBAN',
                                           desc='Pincode to Urban Mapping',
                                           csv_filename='pincode_urban.csv',
                                           ctx=ctx,
                                           post_data_extra={
                                               'rptFileName': 'pincodetoUrbanMapping',
                                           }))

    downloaders.append(DirectoryDownloader(name='CENTRAL_ORG_DETAILS',
                                           desc='list of all central organization details',
                                           csv_filename='central_orgs.csv',
                                           ctx=ctx,
                                           transform=['ignore_if_empty_field', 'Organization Code'],
                                           post_data_extra={
                                               'deptListbyOption': '0',
                                               'rptFileName': 'parentWiseOrganizationDepartmentDetails',
                                               'entityCodes': ['35', '0', '0'],
                                           }))

    downloaders.append(StateWiseDirectoryDownloader(name='PANCHAYAT_MAPPINGS',
                                                    desc='list of all panchayat mappings',
                                                    csv_filename='gp_mapping.csv',
                                                    ctx=ctx,
                                                    download_types=['xls', 'htm'],
                                                    excel_conv_args={
                                                        'header_row_span': 1,
                                                    },
                                                    post_data_extra={
                                                        'rptFileName': 'LocalbodyMappingtoCensusLandregionCode@state',
                                                    }))
    downloaders.append(StateWiseDirectoryDownloader(name='VILLAGES',
                                                    desc='list of all villages',
                                                    csv_filename='villages.csv',
                                                    ctx=ctx,
                                                    excel_conv_args={
                                                        'header_row_span': 2,
                                                    },
                                                    post_data_extra={
                                                        'rptFileName': 'villageofSpecificState@state',
                                                    },
                                                    enrichers={
                                                        'State Code': 'State Code',
                                                        'State Name (In English)': 'State Name(In English)'
                                                    }))
    downloaders.append(StateWiseDirectoryDownloader(name='BLOCK_VILLAGES',
                                                    desc='list of all village to block mappings',
                                                    csv_filename='villages_by_blocks.csv',
                                                    ctx=ctx,
                                                    excel_conv_args={
                                                        'header_row_span': 2,
                                                    },
                                                    post_data_extra={
                                                        'rptFileName': 'subdistrictVillageBlockGpsMapping',
                                                    },
                                                    enrichers={}))
    downloaders.append(StateWiseDirectoryDownloader(name='PRI_LOCAL_BODIES',
                                                    desc='list of all PRI(Panchayati Raj India) local bodies',
                                                    csv_filename='pri_local_bodies.csv',
                                                    ctx=ctx,
                                                    excel_conv_args={
                                                        'header_row_span': 2,
                                                    },
                                                    post_data_extra={
                                                        'rptFileName': 'priLbSpecificState@state',
                                                        'state': 'on',
                                                    }))
    # missing in lgd drop downs and data lacking compared to CONSTITUENCIES_MAPPINGS_PRI and CONSTITUENCIES_MAPPINGS_URBAN
    #downloaders.append(StateWiseDirectoryDownloader(name='CONSTITUENCIES_MAPPINGS',
    #                                                desc='list of all constituencies with local body coverage',
    #                                                csv_filename='constituencies_mapping.csv',
    #                                                ctx=ctx,
    #                                                post_data_extra={
    #                                                    'rptFileName': 'parlimentConstituencyAndAssemblyConstituency@state'
    #                                                },
    #                                                enrichers={
    #                                                    'State Code': 'State Code'
    #                                                }))
    # broken.. 
    #downloaders.append(StateWiseDirectoryDownloader(name='CONSTITUENCIES_MAPPINGS_PRI',
    #                                                desc='list of all constituencies with PRI local body coverage',
    #                                                csv_filename='constituencies_mapping_pri.csv',
    #                                                ctx=ctx,
    #                                                post_data_extra={
    #                                                    'rptFileName': 'parlimentConstituencyAndAssemblyConstituencyPRI@state'
    #                                                },
    #                                                enrichers={
    #                                                    'State Code': 'State Code'
    #                                                }))
    downloaders.append(StateWiseDirectoryDownloader(name='CONSTITUENCIES_MAPPINGS_URBAN',
                                                    desc='list of all constituencies with Urban local body coverage',
                                                    csv_filename='constituencies_mapping_urban.csv',
                                                    ctx=ctx,
                                                    transform=['ignore_if_empty_field', 'Parliament Constituency code'],
                                                    post_data_extra={
                                                        'rptFileName': 'parlimentConstituencyAndAssemblyConstituencyUrban@state'
                                                    },
                                                    enrichers={
                                                        'State Code': 'State Code'
                                                    }))
    downloaders.append(StateWiseDirectoryDownloader(name='PRI_LOCAL_BODY_WARDS',
                                                    desc='list of all PRI Local body wards',
                                                    csv_filename='pri_local_body_wards.csv',
                                                    ctx=ctx,
                                                    post_data_extra={
                                                        'rptFileName': 'priWards@state'
                                                    }))
    downloaders.append(StateWiseDirectoryDownloader(name='URBAN_LOCAL_BODY_WARDS',
                                                    desc='list of all Urban Local body wards',
                                                    csv_filename='urban_local_body_wards.csv',
                                                    ctx=ctx,
                                                    post_data_extra={
                                                        'rptFileName': 'uLBWardforState@state'
                                                    }))
    downloaders.append(StateWiseDirectoryDownloader(name='CONSTITUENCY_COVERAGE',
                                                    desc='list of all assembly/parliament constituencies and their coverage',
                                                    csv_filename='constituency_coverage.csv',
                                                    ctx=ctx,
                                                    transform=['ignore_if_empty_field', 'Parliament Constituency Code'],
                                                    post_data_extra={
                                                        'rptFileName': 'constituencyReport@state'
                                                    }))
 
    downloaders.append(StateWiseDirectoryDownloader(name='STATE_ORG_DETAILS',
                                                    desc='list of all state level organizations',
                                                    csv_filename='state_orgs.csv',
                                                    ctx=ctx,
                                                    transform=['ignore_if_empty_field', 'Organization Code'],
                                                    post_data_extra={
                                                        'rptFileName': 'parentWiseOrganizationDepartmentDetails',
                                                        'deptListbyOption': '2'
                                                    }))



    #downloaders.append(ConstituencyWiseDirectoryDownloader(name='PARLIAMENT_CONSTITUENCIES_LOCAL_BODY_MAPPINGS',
    #                                                       desc='list of all parliament constituencies with local body coverage',
    #                                                       csv_filename='parliament_constituencies_lb_mapping.csv',
    #                                                       ctx=ctx,
    #                                                       post_data_extra={
    #                                                           'rptFileName': 'parliamentConstituency@state#parliament'
    #                                                       }))



    downloaders.append(OrgWiseDirectoryDownloader(name='STATE_ORG_UNITS',
                                                  desc='list of all state level organization units',
                                                  csv_filename='state_org_units.csv',
                                                  depends_on='STATE_ORG_DETAILS',
                                                  ctx=ctx,
                                                  excel_conv_args={
                                                      'header_row_span': 2,
                                                  },
                                                  post_data_extra={
                                                        'rptFileName': 'orgUnitBasedOnOrgCode',
                                                        'state': 'on'
                                                  },
                                                  enrichers={
                                                      'Base Organization Name': 'Organization Name',
                                                      'Base Organization Code': 'Organization Code',
                                                      'State Name': 'State Name',
                                                      'State Code': 'State Code'
                                                  }))
    downloaders.append(OrgWiseDirectoryDownloader(name='CENTRAL_ORG_UNITS',
                                                  desc='list of all central organization units',
                                                  csv_filename='central_org_units.csv',
                                                  depends_on='CENTRAL_ORG_DETAILS',
                                                  ctx=ctx,
                                                  excel_conv_args={
                                                      'header_row_span': 2,
                                                  },
                                                  post_data_extra={
                                                        'rptFileName': 'orgUnitBasedOnOrgCode',
                                                        'state': '0'
                                                  },
                                                  enrichers={
                                                      'Base Organization Name': 'Organization Name',
                                                      'Base Organization Code': 'Organization Code',
                                                  }))
    downloaders.append(OrgWiseDirectoryDownloader(name='STATE_ORG_DESIGNATIONS',
                                                  desc='list of all state level organization designations',
                                                  csv_filename='state_org_designations.csv',
                                                  depends_on='STATE_ORG_DETAILS',
                                                  ctx=ctx,
                                                  post_data_extra={
                                                        'rptFileName': 'designationBasedOnOrgCode',
                                                        'state': 'on'
                                                  },
                                                  enrichers={
                                                      'Base Organization Name': 'Organization Name',
                                                      'Base Organization Code': 'Organization Code',
                                                      'State Name': 'State Name',
                                                      'State Code': 'State Code'
                                                  }))
    downloaders.append(OrgWiseDirectoryDownloader(name='CENTRAL_ORG_DESIGNATIONS',
                                                  desc='list of all central organization designations',
                                                  csv_filename='central_org_designations.csv',
                                                  depends_on='CENTRAL_ORG_DETAILS',
                                                  ctx=ctx,
                                                  post_data_extra={
                                                        'rptFileName': 'designationBasedOnOrgCode',
                                                        'state': '0'
                                                  },
                                                  enrichers={
                                                      'Base Organization Name': 'Organization Name',
                                                      'Base Organization Code': 'Organization Code',
                                                  }))


    downloaders.append(AdminDeptWiseDirectoryDownloader(name='CENTRAL_ADMIN_DEPT_UNITS',
                                                        desc='list of all central adminstrative department units',
                                                        csv_filename='central_admin_dept_units.csv',
                                                        depends_on='CENTRAL_ADMIN_DEPTS',
                                                        ctx=ctx,
                                                        transform=['ignore_if_empty_field', 'Admin Unit Entity Code'],
                                                        post_data_extra={
                                                              'rptFileName': 'adminUnitLevelAdminUnitEntity',
                                                              'state': '0',
                                                        },
                                                        enrichers={
                                                            'Admin Department Name': 'adminLevelNameEng',
                                                            'Admin Department Code': 'adminUnitCode',
                                                        }))
    downloaders.append(AdminDeptWiseDirectoryDownloader(name='STATE_ADMIN_DEPT_UNITS',
                                                        desc='list of all state adminstrative department units',
                                                        csv_filename='state_admin_dept_units.csv',
                                                        depends_on='STATE_ADMIN_DEPTS',
                                                        ctx=ctx,
                                                        transform=['ignore_if_empty_field', 'Admin Unit Entity Code'],
                                                        post_data_extra={
                                                              'rptFileName': 'adminUnitLevelAdminUnitEntity',
                                                              'state': 'on'
                                                        },
                                                        enrichers={
                                                            'Admin Department Name': 'adminLevelNameEng',
                                                            'Admin Department Code': 'adminUnitCode',
                                                            'State Name': 'State Name',
                                                            'State Code': 'State Code'
                                                        }))

    return downloaders

