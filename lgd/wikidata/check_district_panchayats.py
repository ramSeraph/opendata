import csv
from pprint import pprint

from common import (
    base_entity_checks,
    get_entry_from_wd_id,
    get_label,
    get_lgd_codes,
    get_lgd_data,
    get_located_in_ids,
    get_overlap_ids,
    get_wd_data,
    get_wd_entity_lgd_mapping,
    invert_lgd_mapping,
    write_report,
)
from constants import DIST_COUNCIL_OF_INDIA_ID, P_LGD_LOCAL_BODY_CODE, state_info
from filters import filter_district, filter_district_panchayat, filter_state
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

def is_lgd_dist_panchayat(lgd_entry):
    return lgd_entry['Localbody Type Code'] == '1'


def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    
    wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state, 'state')
    wd_state_map_rev = invert_lgd_mapping(wd_state_map)

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
        expected_state_wd_id = wd_state_map_rev.get(expected_lgd_state_code)
        if expected_state_wd_id is None:
            report['wrong_hierarchy'].append({
                'wikidata_id': k,
                'wikidata_label': get_label(v),
                'current': [get_entry_from_wd_id(i) for i in get_located_in_ids(v)],
                'expected': [{'label': f"{lgd_entry['State Name']} (LGD state {expected_lgd_state_code}; Wikidata mapping unresolved)"}],
                'unresolved_state_code': expected_lgd_state_code,
            })
            continue
        expected_state_id = int(expected_state_wd_id[1:])

        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        state_id = located_in_ids[0]
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
    wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state, 'state')
    filtered = get_wd_data(wd_fname, filter_district_panchayat)
    for k,v in filtered.items():
        parent_ids = get_located_in_ids(v)
        if len(parent_ids) != 1:
            continue
        state_lgd_code = wd_state_map.get(f'Q{parent_ids[0]}')
        if state_lgd_code not in state_info:
            continue
        info = state_info[state_lgd_code]
        expected_suffix = info.get('dp_suffix', None)
        if not expected_suffix:
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
        wd_state_map = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state, 'state')
        g_wd_state_map_rev = invert_lgd_mapping(wd_state_map)
    loc_in = g_wd_state_map_rev.get(scode)

    correction_info = {
        'label': label,
        'desc': desc,
        'inst_of': inst_of,
        'loc_in': loc_in,
        'inception': '',
        'lgd_code': lgd_entry['lgd_code'],
        'lgd_code_prop': P_LGD_LOCAL_BODY_CODE,
    }
    if loc_in is None:
        correction_info['unresolved_parent'] = f"{sname} (LGD state {scode})"
    return correction_info

def territory_overlaps_check():
    report = { 'mismatch_territory_overlaps': [] }
    wd_dist_map = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district, 'district')
    wd_dist_map_rev = invert_lgd_mapping(wd_dist_map)
    lgd_dist_data = get_lgd_data('data/lgd/districts.csv', 'District Code')
    dp_to_d, _ = get_district_panchayat_and_district_lgd_mappings()
    filtered = get_wd_data(wd_fname, filter_district_panchayat)
    for k,v in filtered.items():
        label = get_label(v)
        lgd_codes = get_lgd_codes(v)
        if len(lgd_codes) != 1:
            continue
        lgd_code = lgd_codes[0]

        if lgd_code not in dp_to_d:
            print(f'No district mapping for district panchayat LGD code {lgd_code}')
            continue

        overlapping_dist_codes = dp_to_d[lgd_code]
        unresolved = [
            {'lgd_code': code, 'label': f"{lgd_dist_data.get(code, {}).get('District Name(In English)', 'Unknown district')} (LGD district {code}; Wikidata mapping unresolved)"}
            for code in overlapping_dist_codes if code not in wd_dist_map_rev
        ]
        overlapping_dist_ids = {int(wd_dist_map_rev[c][1:]) for c in overlapping_dist_codes if c in wd_dist_map_rev}
        curr_overlap_ids = set(get_overlap_ids(v))
        # An unresolved district may account for a current overlap, so we
        # cannot call any overlap extra until every district is resolved.
        extra = curr_overlap_ids - overlapping_dist_ids if not unresolved else set()
        missing = overlapping_dist_ids - curr_overlap_ids
        if len(extra) == 0 and len(missing) == 0 and not unresolved:
            continue
        entry = {'wikidata_id': k, 'wikidata_label': label,
                 'missing': [get_entry_from_wd_id(i) for i in missing],
                 'extra': [get_entry_from_wd_id(i) for i in extra]}
        if unresolved:
            entry['unresolved'] = unresolved
        report['mismatch_territory_overlaps'].append(entry)
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
                                lgd_code_type='localbody',
                                check_expected_located_in_fn=check_if_located_in_state,
                                wd_fname=wd_fname, wd_filter_fn=filter_district_panchayat,
                                name_prefix_drops=DISTRICT_PANCHAYAT_PREFIXES,
                                name_suffix_drops=DISTRICT_PANCHAYAT_SUFFIXES,
                                name_match_threshold=0.99)
    report.update(hierarchy_check())
    report.update(suffix_check())
    report.update(territory_overlaps_check())
    pprint(report)
    write_report(report, 'district_panchayats.json')

    


