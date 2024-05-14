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
    get_wd_data, get_lgd_data, get_entry_from_wd_id
)

from filters import filter_subdistrict, filter_district, filter_subdivision


lgd_fname = 'data/lgd/subdistricts.csv'
lgd_id_key = 'Sub-district Code'
lgd_name_key = 'Sub-district Name'
wd_fname = 'data/subdistricts.jsonl'

def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    
    wd_dist_map = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)
    wd_dist_map_rev = {v:k for k,v in wd_dist_map.items() }

    filtered_subdivisions = get_wd_data('data/subdivisions.jsonl', filter_subdivision)
    for k,v in filtered_subdivisions.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        v['super_id'] = located_in_ids[0]

    lgd_subdist_data = get_lgd_data(lgd_fname, lgd_id_key)

    filtered = get_wd_data(wd_fname, filter_subdistrict)
    for k,v in filtered.items():
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]
        if lgd_code not in lgd_subdist_data:
            continue
        lgd_entry = lgd_subdist_data[lgd_code]
        expected_lgd_dist_code = lgd_entry['District Code']
        expected_dist_wd_id = wd_dist_map_rev[expected_lgd_dist_code]
        expected_dist_id = int(expected_dist_wd_id[1:])

        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0]
        parent_wd_id = f'Q{parent_id}'
        dist_id = None
        hierarchy = [ parent_id ]
        if parent_wd_id in filtered_subdivisions:
            dist_id = filtered_subdivisions[parent_wd_id]['super_id']
            hierarchy = [ dist_id ] + hierarchy
        else:
            dist_id = parent_id
        if f'Q{dist_id}' not in wd_dist_map or dist_id != expected_dist_id:
            
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(e) for e in hierarchy ],
                                              'expected': [ get_entry_from_wd_id(expected_dist_id) ]})
    return report

def suffix_check():
    report = { 'wrong_suffix': [] }
    by_wid = {}
    for s_code, e in state_info.items():
        e['state_code'] = s_code
        wid = e['wd_id']
        by_wid[wid] = e
        if 'alts' not in e:
            continue
        for e1 in e['alts']:
            e1['state_code'] = s_code
            wid1 = e1['wd_id']
            by_wid[wid1] = e1

    filtered = get_wd_data(wd_fname, filter_subdistrict)
    for k,v in filtered.items():
        inst_of_ids = get_instance_of_ids(v)
        if len(inst_of_ids) != 1:
            continue
        inst_of_wid = f'Q{inst_of_ids[0]}'
        if inst_of_wid not in by_wid:
            continue
        info = by_wid[inst_of_wid]
        expected_suffix = info.get('label_suffix', None)
        if expected_suffix is None:
            expected_suffix = info['suffix']
        label = get_label(v)
        if label.upper().endswith(f' {expected_suffix.upper()}'):
            continue
        report['wrong_suffix'].append({'wikidata_id': k,
                                       'wikidata_label': label,
                                       'expected_suffix': expected_suffix})
    return report

def inst_of_check():
    report = { 'wrong_inst_of': [] }
    lgd_subdist_data = get_lgd_data(lgd_fname, lgd_id_key)

    filtered = get_wd_data(wd_fname, filter_subdistrict)
    for k,v in filtered.items():
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]
        if lgd_code not in lgd_subdist_data:
            continue
        lgd_entry = lgd_subdist_data[lgd_code]
        state_code = lgd_entry['State Code']
        info = state_info[state_code]
        expected_inst_of_wd_ids = [ info['wd_id'] ]
        if 'alts' in info:
            for alt in info['alts']:
                expected_inst_of_wd_ids.append(alt['wd_id'])
        expected_inst_of_ids = [ int(e[1:]) for e in expected_inst_of_wd_ids ]
        inst_of_ids = get_instance_of_ids(v)
        if len(inst_of_ids) != 1:
            continue
        inst_of_id = inst_of_ids[0]
        if inst_of_id in expected_inst_of_ids:
            continue
        label = get_label(v)
        report['wrong_inst_of'].append({'wikidata_id': k,
                                        'wikidata_label': label,
                                        'expected_inst_ofs': [ get_entry_from_wd_id(e) for e in expected_inst_of_ids ],
                                        'current_inst_of': get_entry_from_wd_id(inst_of_id)})
    return report

g_wd_dist_map_rev = None

def get_correction_info(lgd_entry):
    global g_wd_dist_map_rev 
    scode = lgd_entry['State Code']
    info = state_info[scode]

    name = lgd_entry['lgd_name']
    label_suffix = info['label_suffix'] if 'label_suffix' in info else info['suffix']
    label = f'{name} {label_suffix}'

    suffix = info['suffix']
    sname = lgd_entry['State Name']
    dname = lgd_entry['District Name']
    desc = f'{suffix}(sub-district) in {dname} district, {sname}, India'

    inst_of = info['wd_id']

    dcode = lgd_entry['District Code']
    if g_wd_dist_map_rev is None:
        wd_dist_map = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)
        g_wd_dist_map_rev = {v:k for k,v in wd_dist_map.items()}
    loc_in = g_wd_dist_map_rev[dcode]

    i_date = datetime.strptime(lgd_entry['Effective Date'], '%d%b%Y')
    inception = i_date.strftime('+%Y-%m-%dT00:00:00Z/11')
    correction_info = {
        'label': label,
        'desc': desc,
        'inst_of': inst_of,
        'loc_in': loc_in,
        'inception': inception,
        'lgd_code': lgd_entry['lgd_code'],
    }
    return correction_info

wd_dist_data = None
wd_subdiv_data = None
def check_if_located_in_district_or_subdivision(wid):
    global wd_dist_data
    global wd_subdiv_data
    if wd_dist_data is None:
        wd_dist_data = get_wd_data('data/districts.jsonl', filter_district)
        wd_subdiv_data = get_wd_data('data/subdivisions.jsonl', filter_subdivision)
    qid = f'Q{wid}'
    if qid in wd_dist_data or qid in wd_subdiv_data:
        return {'ok': True}
    return {'ok': False, 'expected': 'located in a District or a Subdivision'}



if __name__ == '__main__':
    report = base_entity_checks(entity_type='subdistrict',
                                lgd_fname=lgd_fname,
                                lgd_id_key=lgd_id_key, lgd_name_key=lgd_name_key,
                                lgd_url_fn=lambda x: { 'base': 'https://lgdirectory.gov.in/globalviewSubDistrictDetail.do', 'params': { 'globalsubdistrictId': str(x) }},
                                lgd_correction_fn=get_correction_info,
                                check_expected_located_in_fn=check_if_located_in_district_or_subdivision,
                                wd_fname=wd_fname, wd_filter_fn=filter_subdistrict,
                                name_prefix_drops=['THE '], 
                                name_suffix_drops=[' SUBDISTRICT',
                                                   ' TEHSIL', ' TAHSIL',
                                                   ' TALUKA', ' TALUK', 
                                                   ' MANDAL', ' MANDALAM', ' MANDALA', 
                                                   ' COMMUNITY DEVELOPMENT BLOCK', ' BLOCK', ' C.D.BLOCK',
                                                   ' REVENUE CIRCLE', ' CIRCLE', ' CICLE', ' EAC', ' SDO', ' ADC', ' HQ',
                                                   ' SUBTEHSIL', ' ST',
                                                   ' SUBDIVISION',
                                                   ' P.S.', ' P.S', 'P.S.'],
                                name_match_threshold=0.99)
    report.update(hierarchy_check())
    report.update(suffix_check())
    report.update(inst_of_check())
    pprint(report)
    write_report(report, 'subdistricts.json')

    


