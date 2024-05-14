from pprint import pprint

from common import (
    base_entity_checks, write_report,
    get_label, get_located_in_ids, get_instance_of_ids,
    get_wd_entity_lgd_mapping, get_wd_data,
    get_entry_from_wd_id, state_info, get_contains_ids
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
    pprint(report)
    write_report(report, 'divisions.json')
