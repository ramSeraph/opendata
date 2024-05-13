import json
import csv
from pathlib import Path
from pprint import pprint
from datetime import datetime

from common import (
    base_entity_checks, write_report,
    get_label, get_lgd_codes, state_info,
    get_located_in_ids, get_instance_of_ids,
    get_wd_entity_lgd_mapping,
    get_wd_data, get_lgd_data, get_entry_from_wd_id,
    DIST_COUNCIL_OF_INDIA_ID
)

from filters import filter_state, filter_district_panchayat


lgd_fname = 'data/lgd/pri_local_bodies.csv'
lgd_id_key = 'Localbody Code'
lgd_name_key = 'Localbody Name (In English)'
wd_fname = 'data/district_panchayats.jsonl'

def is_lgd_dist_panchayat(lgd_entry):
    if lgd_entry['Localbody Type Code'] == '1':
        return True
    return False


def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    
    wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state)
    wd_state_map_rev = {v:k for k,v in wd_state_map.items() }

    lgd_dist_panchayat_data = get_lgd_data(lgd_fname, lgd_id_key, filter_fn=is_lgd_dist_panchayat)

    filtered = get_wd_data(wd_fname, filter_district_panchayat)
    for k,v in filtered.items():
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]
        if lgd_code not in lgd_dist_panchayat_data:
            continue
        lgd_entry = lgd_dist_panchayat_data[lgd_code]
        expected_lgd_state_code = lgd_entry['State Code']
        expected_state_wd_id = wd_state_map_rev[expected_lgd_state_code]
        expected_state_id = int(expected_state_wd_id[1:])

        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        state_id = located_in_ids[0]
        state_wd_id = f'Q{state_id}'
        hierarchy = [ state_id ]
        if f'Q{state_id}' not in wd_state_map or state_id != expected_state_id:
            
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(e) for e in hierarchy ],
                                              'expected': [ get_entry_from_wd_id(expected_state_id) ]})
    return report


def suffix_check():
    report = { 'wrong_suffix': [] }
    by_wid = {}
    for s_code, e in state_info.items():
        e['state_code'] = s_code
        wid = e['wd_id']
        by_wid[wid] = e

    wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state)
    filtered = get_wd_data(wd_fname, filter_district_panchayat)
    for k,v in filtered.items():
        inst_of_ids = get_instance_of_ids(v)
        if len(inst_of_ids) != 1:
            continue
        inst_of_wid = f'Q{inst_of_ids[0]}'
        if inst_of_wid not in wd_state_map:
            continue
        state_lgd_code = wd_state_map[inst_of_wid]
        info = state_info[state_lgd_code]
        expected_suffix = info.get('dp_suffix', None)
        if expected_suffix is None:
            continue
        label = get_label(v)
        if label.upper().endswith(f' {expected_suffix.upper()}'):
            continue
        report['wrong_suffix'].append({'wikidata_id': k,
                                       'wikidata_label': label,
                                       'expected_suffix': expected_suffix})
    return report


g_wd_state_map_rev = None

def get_correction_info(lgd_entry):
    global g_wd_state_map_rev 
    scode = lgd_entry['State Code']
    info = state_info[scode]

    name = lgd_entry['lgd_name']
    label_suffix = info['dp_suffix']
    label = f'{name} {label_suffix}' if label_suffix != '' else name

    suffix = info.get('dp_suffix', ' District Panchayat')
    sname = lgd_entry['State Name']
    desc = f'{suffix} in {sname}, India'

    inst_of = f'Q{DIST_COUNCIL_OF_INDIA_ID}'

    if g_wd_state_map_rev is None:
        wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state)
        g_wd_state_map_rev = {v:k for k,v in wd_state_map.items()}
    loc_in = g_wd_state_map_rev[scode]

    #i_date = datetime.strptime(lgd_entry['Effective Date'], '%d%b%Y')
    #inception = i_date.strftime('+%Y-%m-%dT00:00:00Z/11')
    correction_info = {
        'label': label,
        'desc': desc,
        'inst_of': inst_of,
        'loc_in': loc_in,
        'inception': '',
        'lgd_code': lgd_entry['lgd_code'],
    }
    return correction_info

wd_state_data = None
def check_if_located_in_state(wid):
    global wd_state_data
    if wd_state_data is None:
        wd_state_data = get_wd_data('data/states.jsonl', filter_state)
    qid = f'Q{wid}'
    if qid in wd_state_data:
        return {'ok': True}
    return {'ok': False, 'expected': 'located in a State or Union Territory'}



if __name__ == '__main__':
    report = base_entity_checks(entity_type='district_panchayat',
                                lgd_fname=lgd_fname,
                                lgd_id_key=lgd_id_key, lgd_name_key=lgd_name_key, lgd_filter_fn=is_lgd_dist_panchayat,
                                lgd_url_fn=lambda x: { 'base': 'https://lgdirectory.gov.in/viewEntityDetail.do', 'params': { 'code': str(x), 'isState': "'N'" }},
                                lgd_correction_fn=get_correction_info,
                                lgd_get_effective_date=False,
                                check_expected_located_in_fn=check_if_located_in_state,
                                wd_fname=wd_fname, wd_filter_fn=filter_district_panchayat,
                                name_prefix_drops=[ 'DISTRICT PANCHAYAT OF' ], 
                                name_suffix_drops=[' DISTRICT PANCHAYAT', ' DISTRICT',
                                                   ' ZILLA PARISHAD', ' ZILLA PANCHAYAT', ' ZILA PARISHAD',
                                                   ' DISTRICT PLANNING AND DEVELOPMENT BOARD'],
                                name_match_threshold=0.99)
    report.update(hierarchy_check())
    report.update(suffix_check())
    #report.update(inst_of_check())
    pprint(report)
    write_report(report, 'district_panchayats.json')

    


