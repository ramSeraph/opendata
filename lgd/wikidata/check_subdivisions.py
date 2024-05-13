from pprint import pprint

from common import (
    base_entity_checks, write_report,
    get_label, get_located_in_ids, get_instance_of_ids,
    get_wd_entity_lgd_mapping, get_wd_data,
    get_entry_from_wd_id, get_lgd_data, state_info
)

from filters import filter_district, filter_subdivision


wd_fname = 'data/subdivisions.jsonl'
def hierarchy_check():
    report = { 'wrong_hierarchy': [] }
    dist_mapping = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)

    filtered = get_wd_data(wd_fname, filter_subdivision)
    for k,v in filtered.items():
        located_in_ids = get_located_in_ids(v)
        if len(located_in_ids) != 1:
            continue
        parent_id = located_in_ids[0] 
        parent_wid = f'Q{parent_id}'
        if parent_wid not in dist_mapping:
            label = get_label(v)
            report['wrong_hierarchy'].append({'wikidata_id': k,
                                              'wikidata_label': label,
                                              'current': [ get_entry_from_wd_id(parent_id) ],
                                              'expected': [{ 'label': 'Any District of India' }]})

    return report

def inst_of_check():
    report = { 'wrong_inst_of': [] }

    dist_lgd_map = get_lgd_data('data/lgd/districts.csv', 'District Code')
    dist_mapping = get_wd_entity_lgd_mapping('data/districts.jsonl', filter_district)
    filtered = get_wd_data(wd_fname, filter_subdivision)
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
        if parent_wid not in dist_mapping:
            continue

        dist_lgd_id = dist_mapping[parent_wid]
        if dist_lgd_id not in dist_lgd_map:
            continue
        state_lgd_id = dist_lgd_map[dist_lgd_id]['State Code']

        info = state_info[state_lgd_id]
        if 'wd_subdiv_id' not in info:
            #TODO: this should be flagged
            continue

        wd_subdiv_id = info['wd_subdiv_id']
        expected_inst_of_id = int(wd_subdiv_id[1:])
        if inst_of_id == expected_inst_of_id:
            continue
        label = get_label(v)
        report['wrong_inst_of'].append({'wikidata_id': k,
                                        'wikidata_label': label,
                                        'expected_inst_ofs': [ get_entry_from_wd_id(expected_inst_of_id) ],
                                        'current_inst_of': get_entry_from_wd_id(inst_of_id)})
    return report


wd_dist_data = None
def check_if_located_in_district(wid):
    global wd_dist_data
    if wd_dist_data is None:
        wd_dist_data = get_wd_data('data/districts.jsonl', filter_district)
    qid = f'Q{wid}'
    if qid in wd_dist_data:
        return {'ok': True}
    return {'ok': False, 'expected': 'located in a District'}



if __name__ == '__main__':
    report = base_entity_checks(entity_type='subdivision',
                                has_lgd=False,
                                check_expected_located_in_fn=check_if_located_in_district,
                                wd_fname=wd_fname, wd_filter_fn=filter_subdivision)
    report.update(hierarchy_check())
    report.update(inst_of_check())
    #report.update(suffix_check())
    pprint(report)
    write_report(report, 'subdivisions.json')
