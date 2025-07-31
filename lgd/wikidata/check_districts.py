from pprint import pprint
from datetime import datetime

from common import (
    base_entity_checks, write_report,
    get_label, get_lgd_codes,
    get_located_in_ids, get_wd_entity_lgd_mapping,
    get_wd_data, get_lgd_data, get_entry_from_wd_id,
    P_LGD_DIST_CODE
)

from filters import filter_district, filter_state, filter_division
from suffixes import DISTRICT_PREFIXES, DISTRICT_SUFFIXES

lgd_fname = 'data/lgd/districts.csv'
lgd_id_key = 'District Code'
lgd_name_key = 'District Name(In English)'
wd_fname = 'data/districts.jsonl'

def hierarchy_check():
    report = { 'wrong_hierarchy': [] }

    wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state, 'state')
    wd_state_map_rev = {v:k for k,v in wd_state_map.items() }

    filtered_divisions = get_wd_data('data/divisions.jsonl', filter_division)
    for k,v in filtered_divisions.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        v['super_id'] = located_in_ids[0]

    lgd_dist_data = get_lgd_data(lgd_fname, lgd_id_key)

    filtered = get_wd_data(wd_fname, filter_district)
    for k,v in filtered.items():
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]
        if lgd_code not in lgd_dist_data:
            continue
        lgd_entry = lgd_dist_data[lgd_code]
        expected_lgd_state_code = lgd_entry['State Code']
        expected_state_wd_id = wd_state_map_rev[expected_lgd_state_code]
        expected_state_id = int(expected_state_wd_id[1:])

        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0]
        parent_wd_id = f'Q{parent_id}'
        state_id = None
        hierarchy = [ parent_id ]
        if parent_wd_id in filtered_divisions:
            state_id = filtered_divisions[parent_wd_id]['super_id']
            hierarchy = [ state_id ] + hierarchy
        else:
            state_id = parent_id
        if f'Q{state_id}' not in wd_state_map or state_id != expected_state_id:
            
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(e) for e in hierarchy ],
                                              'expected': [ get_entry_from_wd_id(expected_state_id) ]})

    return report


def suffix_check():
    report = { 'wrong_suffix': [] }
    filtered = get_wd_data(wd_fname, filter_district)

    for k,v in filtered.items():
        label = get_label(v)
        if label.upper().endswith(' DISTRICT'):
            continue
        report['wrong_suffix'].append({'wikidata_id': k,
                                       'wikidata_label': label,
                                       'expected_suffix': ' district'})
    return report

g_wd_state_map_rev = None

def get_correction_info(lgd_entry):
    global g_wd_state_map_rev 
    scode = lgd_entry['State Code']

    name = lgd_entry['lgd_name']
    label = f'{name} district'

    sname = lgd_entry['State Name (In English)']
    desc = f'district in {sname}, India'

    inst_of = 'Q{DIST_ID}'

    if g_wd_state_map_rev is None:
        wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state, 'state')
        g_wd_state_map_rev = {v:k for k,v in wd_state_map.items()}
    loc_in = g_wd_state_map_rev[scode]

    i_date = datetime.strptime(lgd_entry['Effective Date'], '%d%b%Y')
    inception = i_date.strftime('+%Y-%m-%dT00:00:00Z/11')
    correction_info = {
        'label': label,
        'desc': desc,
        'inst_of': inst_of,
        'loc_in': loc_in,
        'inception': inception,
        'lgd_code': lgd_entry['lgd_code'],
        'lgd_code_prop': P_LGD_DIST_CODE,
    }
    return correction_info


wd_state_data = None
wd_div_data = None
def check_if_located_in_state_or_division(wid):
    global wd_state_data
    global wd_div_data
    if wd_state_data is None:
        wd_state_data = get_wd_data('data/states.jsonl', filter_state)
        wd_div_data = get_wd_data('data/divisions.jsonl', filter_division)
    qid = f'Q{wid}'
    if qid not in wd_state_data and qid not in wd_div_data:
        return {'ok': False, 'expected': 'located in a State or a Division'}
    return {'ok': True}



if __name__ == '__main__':
    report = base_entity_checks(entity_type='district',
                                lgd_fname=lgd_fname, lgd_id_key=lgd_id_key, lgd_name_key=lgd_name_key,
                                lgd_url_fn=lambda x: { 'base': 'https://lgdirectory.gov.in/globalviewDistrictDetail.do', 'params': {'globaldistrictId':str(x)}},
                                lgd_correction_fn=get_correction_info,
                                lgd_code_type='district',
                                check_expected_located_in_fn=check_if_located_in_state_or_division,
                                wd_fname=wd_fname, wd_filter_fn=filter_district,
                                name_prefix_drops=DISTRICT_PREFIXES, name_suffix_drops=DISTRICT_SUFFIXES, name_match_threshold=0.0)
    report.update(hierarchy_check())
    report.update(suffix_check())
    pprint(report)
    write_report(report, 'districts.json')
