from pprint import pprint

from common import (
    base_entity_checks, write_report,
    get_label, get_located_in_ids, get_instance_of_ids,
    get_wd_entity_lgd_mapping, get_wd_data,
    get_entry_from_wd_id, state_info, get_contains_ids,
    get_lgd_data
)

from filters import filter_state, filter_division, filter_district


wd_fname = 'data/divisions.jsonl'
def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    state_mapping = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state)

    filtered = get_wd_data(wd_fname, filter_division)
    for k,v in filtered.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0] 
        parent_wid = f'Q{parent_id}'
        if parent_wid not in state_mapping:
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(parent_id) ],
                                              'expected': [{ 'label': 'Any State of India' }]})

    return report

def suffix_check():
    report = { 'wrong_suffix': [] }
    filtered = get_wd_data(wd_fname, filter_division)

    for k,v in filtered.items():
        label = get_label(v)
        if label.upper().endswith(' DIVISION'):
            continue
        report['wrong_suffix'].append({'wikidata_id': k,
                                       'wikidata_label': label,
                                       'expected_suffix': ' division'})
    return report

def inst_of_check():
    report = { 'wrong_inst_of': [] }

    state_mapping = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state)
    filtered = get_wd_data(wd_fname, filter_division)
    for k,v in filtered.items():
        inst_of_ids = get_instance_of_ids(v)
        if len(inst_of_ids) != 1:
            continue
        inst_of_id = inst_of_ids[0]

        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0] 
        parent_wid = f'Q{parent_id}'
        if parent_wid not in state_mapping:
            continue

        info = state_info[state_mapping[parent_wid]]
        if 'wd_div_id' in info:
            wd_div_id = info['wd_div_id']
            expected_inst_of_id = int(wd_div_id[1:])
            if inst_of_id == expected_inst_of_id:
                continue
            expected_inst_of_entry = get_entry_from_wd_id(expected_inst_of_id)
        else:
            state_name = info['name']
            expected_inst_of_entry = {'label': f'division of {state_name}'}

        label = get_label(v)
        report['wrong_inst_of'].append({'wikidata_id': k,
                                        'wikidata_label': label,
                                        'expected_inst_ofs': [ expected_inst_of_entry ],
                                        'current_inst_of': get_entry_from_wd_id(inst_of_id)})
    return report

def expected_contains_check():
    report = { 'wrong_kind_of_contains': [] }
    filtered_dists = get_wd_data('data/districts.jsonl', filter_district)
    filtered = get_wd_data(wd_fname, filter_division)
    for k,v in filtered.items():
        contains_ids = get_contains_ids(v)
        not_districts = []
        for i in contains_ids:
            wid = f'Q{i}'
            if wid not in filtered_dists:
                not_districts.append(i)
        if len(not_districts) > 0:
            label = get_label(v)
            report['wrong_kind_of_contains'].append({'wikidata_id': k,
                                                     'wikidata_label': label,
                                                     'contains': [ { 'expected': 'District of India', 'curr': get_entry_from_wd_id(e) } for e in not_districts ]})
    return report

def contains_completeness_check():
    report = { 'mismatch_in_contains': [] }
    dists_by_state = {}
    dist_mapping = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)
    lgd_dist_data = get_lgd_data('data/lgd/districts.csv', 'District Code')
    filtered_dists = get_wd_data('data/districts.jsonl', filter_district)
    for k,v in filtered_dists.items():
        if dist_mapping[k] == 'NA':
            continue
        lgd_entry = lgd_dist_data[dist_mapping[k]]
        state_code = lgd_entry['State Code']
        state_name = lgd_entry['State Name (In English)']
        if state_code not in dists_by_state:
            dists_by_state[state_code] = {'state_name': state_name, 'entries': []}
        dists_by_state[state_code]['entries'].append({'id': k, 'label': get_label(v)})

    state_mapping = get_wd_entity_lgd_mapping('data/states.jsonl', filter_state)
    lgd_state_data = get_lgd_data('data/lgd/states.csv', 'State Code')
    filtered = get_wd_data('data/divisions.jsonl', filter_division)
    dists_by_state_from_divs = {}
    divs_by_state = {}
    divs_by_dist = {}
    for k,v in filtered.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0]
        parent_wid = f'Q{parent_id}'
        scode = state_mapping[parent_wid]
        lgd_entry = lgd_state_data[scode]
        state_code = lgd_entry['State Code']
        state_name = lgd_entry['State Name(In English)']
        contains_ids = get_contains_ids(v)
        if state_code not in dists_by_state_from_divs:
            dists_by_state_from_divs[state_code] = {'state_name': state_name, 'entries': [], 'state_wid': parent_wid}
        dists_by_state_from_divs[state_code]['entries'] += [ f'Q{i}' for i in contains_ids ] 
        if scode not in divs_by_state:
            divs_by_state[scode] = []
        divs_by_state[scode].append({ 'id': k, 'label': get_label(v) })
        for c in contains_ids:
            divs_by_dist[c] = k

    for scode, info in dists_by_state_from_divs.items():
        dists_in_divs = set(info['entries'])
        all_state_dists = set([ e['id'] for e in dists_by_state[scode]['entries'] ])
        missing_in_divs = all_state_dists - dists_in_divs
        extra_in_divs = dists_in_divs - all_state_dists
        if len(missing_in_divs) > 0 or len(extra_in_divs) > 0:
            report['mismatch_in_contains'].append({'parent': get_entry_from_wd_id(info['state_wid'][1:]),
                                                   'children': divs_by_state[scode],
                                                   'missing': [ get_entry_from_wd_id(wid[1:]) for wid in missing_in_divs ],
                                                   'extra': [ {'element': get_entry_from_wd_id(wid[1:]), 'child': get_entry_from_wd_id(divs_by_dist[wid])} for wid in extra_in_divs ]})
    return report

wd_state_data = None
def check_if_located_in_state(wid):
    global wd_state_data
    if wd_state_data is None:
        wd_state_data = get_wd_data('data/states.jsonl', filter_state)
    qid = f'Q{wid}'
    if qid in wd_state_data:
        return {'ok': True}
    return {'ok': False, 'expected': 'located in a State'}



if __name__ == '__main__':
    report = base_entity_checks(entity_type='division',
                                has_lgd=False,
                                check_expected_located_in_fn=check_if_located_in_state,
                                wd_fname=wd_fname, wd_filter_fn=filter_division)
    report.update(hierarchy_check())
    report.update(suffix_check())
    report.update(inst_of_check())
    report.update(expected_contains_check())
    report.update(contains_completeness_check())
    pprint(report)
    write_report(report, 'divisions.json')
