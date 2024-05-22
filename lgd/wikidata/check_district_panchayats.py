import json
import csv
from pathlib import Path
from pprint import pprint
from datetime import datetime

from common import (
    base_entity_checks, write_report,
    get_label, get_lgd_codes, state_info,
    get_located_in_ids, get_instance_of_ids,
    get_wd_entity_lgd_mapping, get_coextensive_ids,
    get_overlap_ids,
    get_wd_data, get_lgd_data, get_entry_from_wd_id,
    DIST_COUNCIL_OF_INDIA_ID
)

from filters import filter_state, filter_district_panchayat, filter_district

from suffixes import DISTRICT_PANCHAYAT_PREFIXES, DISTRICT_PANCHAYAT_SUFFIXES

lgd_fname = 'data/lgd/pri_local_bodies.csv'
lgd_id_key = 'Localbody Code'
lgd_name_key = 'Localbody Name (In English)'
wd_fname = 'data/district_panchayats.jsonl'

def get_district_panchayat_and_district_lgd_mappings():
    dp_to_d = {}
    d_to_dp = {}
    with open('data/lgd/district_panchayats.csv', 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            dp_code = r['District Panchayat Code']
            d_code = r['Disrict Code']
            if dp_code not in dp_to_d:
                dp_to_d[dp_code] = []
            dp_to_d[dp_code].append(d_code)
            if d_code not in d_to_dp:
                d_to_dp[d_code] = []
            d_to_dp[d_code].append(dp_code)
    return (dp_to_d, d_to_dp)

g_dp_to_d = None
g_d_to_dp = None

def get_coextensive_district(dp_code):
    global g_dp_to_d
    global g_d_to_dp

    if g_dp_to_d is None:
        g_dp_to_d, g_d_to_dp = get_district_panchayat_and_district_lgd_mappings()

    dist_codes = g_dp_to_d[dp_code]
    if len(dist_codes) != 1:
        return None
    dist_code = dist_codes[0]
    dp_codes_for_dist = g_d_to_dp[dist_code]
    if len(dp_codes_for_dist) != 1:
        return None
    return dist_code


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

def territory_overlaps_check():
    report = { 'mismatch_territory_overlaps': [] }
    wd_dist_map = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)
    wd_dist_map_rev = {v:k for k,v in wd_dist_map.items()}
    dp_to_d, d_to_dp = get_district_panchayat_and_district_lgd_mappings()
    filtered = get_wd_data(wd_fname, filter_district_panchayat)
    for k,v in filtered.items():
        label = get_label(v)
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]
        overlapping_dist_codes = dp_to_d[lgd_code]
        overlapping_dist_ids = set([ int(wd_dist_map_rev[c][1:]) for c in overlapping_dist_codes ])
        curr_overlap_ids = set(get_overlap_ids(v))
        extra = curr_overlap_ids - overlapping_dist_ids
        missing = overlapping_dist_ids - curr_overlap_ids
        if len(extra) == 0 and len(missing) == 0:
            continue
        report['mismatch_territory_overlaps'].append({'wikidata_id': k, 'wikidata_label': label,
                                                      'missing': [ get_entry_from_wd_id(i) for i in missing ],
                                                      'extra': [ get_entry_from_wd_id(i) for i in extra ]})
    return report
   
def coextensiveness_check():
    report = {'muliple_coextensive_withs': [],
              'missing_coextensive_with': [],
              'wrong_coextensive_with': [],
              'missing_rev_coextensive_with': []}

    wd_dist_map = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)
    wd_dist_map_rev = {v:k for k,v in wd_dist_map.items()}
    filtered_dists = get_wd_data('data/districts.jsonl', filter_district)
    filtered = get_wd_data(wd_fname, filter_district_panchayat)
    for k,v in filtered.items():
        label = get_label(v)
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]
        dcode = get_coextensive_district(lgd_code)
        d_wd_id = None
        if dcode is not None:
            d_wd_id = wd_dist_map_rev[dcode]
            dist_v = filtered_dists[d_wd_id]
            d_coex_ids = get_coextensive_ids(dist_v)
            if k[1:] not in d_coex_ids:
                report['missing_rev_coextensive_with'].append({ 'wikidata_id': k, 'wikidata_label': label,
                                                                'expected_in': get_entry_from_wd_id(d_wd_id[1:]) })

        coex_ids = get_coextensive_ids(v)
        if len(coex_ids) == 0:
            if dcode is None:
                continue
            report['missing_coextensive_with'].append({ 'wikidata_id': k, 'wikidata_label': label,
                                                        'expected': get_entry_from_wd_id(d_wd_id[1:]) })
            continue
        if len(coex_ids) > 1:
            report['multiple_coextensive_with'].append({ 'wikidata_id': k, 'wikidata_label': label,
                                                         'current': [ get_entry_from_wd_id(e) for e in coex_ids ] })
            continue

        coex_id = coex_ids[0]
        coex_wd_id = f'Q{coex_id}'
        if coex_wd_id == d_wd_id:
            continue

        report['wrong_coextensive_with'].append({ 'wikidata_id': k, 'wikidata_label': label,
                                                  'current': get_entry_from_wd_id(coex_id),
                                                  'expected': get_entry_from_wd_id(d_wd_id[1:]) })

    return report

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
                                name_prefix_drops=DISTRICT_PANCHAYAT_PREFIXES,
                                name_suffix_drops=DISTRICT_PANCHAYAT_SUFFIXES,
                                name_match_threshold=0.99)
    report.update(hierarchy_check())
    report.update(suffix_check())
    report.update(territory_overlaps_check())
    #report.update(coextensiveness_check())
    #report.update(inst_of_check())
    pprint(report)
    write_report(report, 'district_panchayats.json')

    


